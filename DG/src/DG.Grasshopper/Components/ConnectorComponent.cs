#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Services;
using DG.Grasshopper.Params;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class ConnectorComponent : GH_Component
{
    // Phase 825 (CONNG-03): the platform token is the single credential. It is
    // authenticated by data-service, which returns the project scope and the
    // Neo4j connection bundle — so the component needs no URI/User/Password/
    // Database/Project/DataServiceUrl inputs. data-service base URL is a compile
    // default (ADR-825-4); a future CONN-F can re-expose it.
    private const string DataServiceUrl = "http://localhost:8000";

    private readonly INeo4jConnectorService _connectorService = new Neo4jConnectorService();
    private readonly IConnectorHeartbeatClient _heartbeatClient = new ConnectorHeartbeatClient();
    private Task<ConnectResult>? _connectTask;
    private CancellationTokenSource? _connectCts;
    private string _activeRequestKey = string.Empty;
    private HeartbeatResult _latestAuth = HeartbeatResult.NotAttempted;
    private ConnectionInfo _latestConnection = new()
    {
        IsConnected = false,
        StatusMessage = "Idle",
    };

    public ConnectorComponent()
        : base("CONNECTOR", "CONNECTOR", "Connect to Neo4j for DG validation using a platform token.", DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
    {
    }

    // ADR-825-3: a fresh GUID (was 24E78A17-…). The input surface changed from 8
    // ports to 2, so old canvases intentionally show a missing-component
    // placeholder rather than silently rebinding old panels by index.
    public override Guid ComponentGuid => new("3F9B1C7E-6A24-4D53-8E10-9C2A5B7D40F1");

    protected override Bitmap Icon => DgIcons.Connector24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        // Token: a custom non-persistent param so a typed/pasted value is usable
        // live but is never serialized into the .gh (SC-6). Optional so the
        // component can show its own "Awaiting token" feedback instead of GH's
        // generic collect-data error.
        pManager.AddParameter(
            new NonPersistentStringParam(),
            "Platform Token",
            "Token",
            "Platform credential (dgc_… token minted from the Connectors screen, Grasshopper connector). It resolves the project and Neo4j connection — no other inputs are needed.",
            GH_ParamAccess.item);
        pManager.AddBooleanParameter("Connect", "Go", "Set true to authenticate the token and connect", GH_ParamAccess.item, false);
        pManager[0].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Database", "Database", "DG connection object from CONNECTOR", GH_ParamAccess.item);
        pManager.AddTextParameter("Project", "Project", "Project name resolved from the platform token", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var token = string.Empty;
        var connect = false;

        da.GetData(0, ref token);
        da.GetData(1, ref connect);

        if (!connect)
        {
            CancelPendingConnection();
            _latestConnection = NotConnected("Connection prepared. Set Connect=true to authenticate the token and connect.");
            _latestAuth = HeartbeatResult.NotAttempted;
            Message = "Idle";
        }
        else if (string.IsNullOrWhiteSpace(token))
        {
            CancelPendingConnection();
            _latestConnection = NotConnected("No platform token supplied.");
            _latestAuth = HeartbeatResult.NotAttempted;
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ConnectorTokenMissing());
            Message = "Awaiting token";
        }
        else
        {
            var requestKey = HashToken(token);
            if (_connectTask is null || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
            {
                StartConnection(token, requestKey);
            }

            if (_connectTask is { IsCompletedSuccessfully: true })
            {
                var result = _connectTask.Result;
                _latestConnection = result.Connection;
                _latestAuth = result.Auth;
                Message = (_latestConnection.IsConnected ? "Connected" : "Connect failed") + AuthSuffix(_latestAuth.Outcome);
                ReportAuth(_latestAuth);
            }
            else if (_connectTask is { IsFaulted: true })
            {
                var error = _connectTask.Exception?.GetBaseException().Message ?? "Connection task failed.";
                _latestConnection = NotConnected(error);
                _latestAuth = HeartbeatResult.NotAttempted;
                Message = "Connect failed";
            }
            else if (_connectTask is { IsCanceled: true })
            {
                _latestConnection = NotConnected("Connection canceled.");
                _latestAuth = HeartbeatResult.NotAttempted;
                Message = "Canceled";
            }
            else
            {
                Message = "Connecting...";
            }
        }

        // The connection is derived entirely from the authenticated token (ADR-825-6):
        // no bundle → no live connection, and the Database output carries a
        // not-connected ConnectionInfo describing why.
        da.SetData(0, _latestConnection);
        da.SetData(1, _latestConnection.Project);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        CancelPendingConnection();
        base.RemovedFromDocument(document);
    }

    private void StartConnection(string token, string requestKey)
    {
        CancelPendingConnection();

        _activeRequestKey = requestKey;
        _latestConnection = NotConnected("Authenticating platform token...");
        _connectCts = new CancellationTokenSource();
        _connectTask = RunConnectAsync(token, _connectCts.Token);

        _ = _connectTask.ContinueWith(
            _ =>
            {
                var doc = OnPingDocument();
                doc?.ScheduleSolution(1, _ => ExpireSolution(false));
            },
            TaskScheduler.Default);
    }

    private async Task<ConnectResult> RunConnectAsync(string token, CancellationToken cancellationToken)
    {
        var auth = await _heartbeatClient.CheckAsync(DataServiceUrl, token, cancellationToken).ConfigureAwait(false);

        // Only an authenticated token yields a connection bundle; otherwise there
        // is nothing to connect with, so we skip the bolt attempt entirely and
        // report the auth reason on a not-connected ConnectionInfo.
        if (auth.Outcome != HeartbeatOutcome.Authenticated || auth.Bundle is not { } bundle)
        {
            var reason = auth.Outcome switch
            {
                HeartbeatOutcome.Rejected => "Platform token rejected — invalid, revoked, or expired.",
                HeartbeatOutcome.Unreachable => "Could not reach data-service to authenticate the token.",
                _ => "No platform token.",
            };
            return new ConnectResult(NotConnected(reason), auth);
        }

        var request = new ConnectionInfo
        {
            Uri = bundle.Uri ?? "bolt://localhost:7687",
            User = bundle.User ?? "neo4j",
            Password = bundle.Password ?? string.Empty,
            Database = bundle.Database ?? "neo4j",
            Project = bundle.Project ?? "default-project",
        };

        var connection = await _connectorService.TryConnectAsync(request, cancellationToken).ConfigureAwait(false);
        return new ConnectResult(connection, auth);
    }

    private void ReportAuth(HeartbeatResult auth)
    {
        switch (auth.Outcome)
        {
            case HeartbeatOutcome.Rejected:
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ErrorMessageTemplates.ConnectorTokenRejected());
                break;
            case HeartbeatOutcome.Unreachable:
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ConnectorHeartbeatUnreachable(DataServiceUrl));
                break;
        }
    }

    private void CancelPendingConnection()
    {
        try
        {
            _connectCts?.Cancel();
        }
        catch
        {
            // no-op: cancellation is best-effort.
        }
        finally
        {
            _connectCts?.Dispose();
            _connectCts = null;
            _connectTask = null;
            _activeRequestKey = string.Empty;
        }
    }

    private static ConnectionInfo NotConnected(string status) => new()
    {
        IsConnected = false,
        StatusMessage = status,
    };

    private static string AuthSuffix(HeartbeatOutcome outcome)
    {
        return outcome switch
        {
            HeartbeatOutcome.Authenticated => " · Auth OK",
            HeartbeatOutcome.Rejected => " · Auth failed",
            HeartbeatOutcome.Unreachable => " · Auth unreachable",
            _ => string.Empty,
        };
    }

    private static string HashToken(string token)
    {
        // The raw token never enters the dedup key — only its SHA-256 hash.
        return Convert.ToHexString(
            System.Security.Cryptography.SHA256.HashData(
                System.Text.Encoding.UTF8.GetBytes(token ?? string.Empty)));
    }

    private readonly record struct ConnectResult(ConnectionInfo Connection, HeartbeatResult Auth);
}
#else
namespace DG.Grasshopper.Components;

public sealed class ConnectorComponent
{
}
#endif
