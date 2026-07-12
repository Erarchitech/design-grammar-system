#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;
using System.Drawing;
using System.Security.Cryptography;
using System.Text;

namespace DG.Grasshopper.Components;

public sealed class ConnectorComponent : GH_Component
{
    private readonly INeo4jConnectorService _connectorService = new Neo4jConnectorService();
    private readonly IConnectorHeartbeatClient _heartbeatClient = new ConnectorHeartbeatClient();
    private Task<ConnectResult>? _connectTask;
    private CancellationTokenSource? _connectCts;
    private string _activeRequestKey = string.Empty;
    private HeartbeatResult _latestAuth = HeartbeatResult.NotAttempted;
    private ConnectionInfo _latestConnection = new()
    {
        Uri = "bolt://localhost:7687",
        User = "neo4j",
        Password = "12345678",
        Database = "neo4j",
        Project = "default-project",
        IsConnected = false,
        StatusMessage = "Idle",
    };

    public ConnectorComponent()
        : base("CONNECTOR", "CONNECTOR", "Connect to Neo4j for DG validation.", DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
    {
    }

    public override Guid ComponentGuid => new("24E78A17-4533-44E7-8931-1224A70A1B36");

    protected override Bitmap Icon => DgIcons.Connector24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddTextParameter("Neo4jURI", "URI", "Neo4j bolt URI", GH_ParamAccess.item, "bolt://localhost:7687");
        pManager.AddTextParameter("Neo4jUser", "User", "Neo4j user", GH_ParamAccess.item, "neo4j");
        pManager.AddTextParameter("Neo4jPassword", "Password", "Neo4j password", GH_ParamAccess.item, "12345678");
        pManager.AddTextParameter("Database", "DB", "Neo4j database", GH_ParamAccess.item, "neo4j");
        pManager.AddTextParameter("PROJECT NAME", "Project", "Project name (dg:project annotation)", GH_ParamAccess.item, "default-project");
        pManager.AddBooleanParameter("Connect", "Go", "Set true to connect", GH_ParamAccess.item, false);
        // Additive optional inputs (Phase 824). Appended at indices 6-7 so the existing
        // inputs 0-5, their wiring, and the component GUID stay unchanged for saved canvases.
        pManager.AddTextParameter("DataServiceUrl", "DataServiceUrl", "DG data-service base URL for platform-token auth", GH_ParamAccess.item, "http://localhost:8000");
        pManager.AddTextParameter("Platform Token", "Token", "Optional platform credential (dgc_… token minted from the Connectors screen, Grasshopper connector). Wire from a Panel — never internalised.", GH_ParamAccess.item, "");
        pManager[6].Optional = true;
        pManager[7].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Database", "Database", "DG connection object from CONNECTOR", GH_ParamAccess.item);
        pManager.AddTextParameter("Project", "Project", "Project name (passthrough of PROJECT NAME input)", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var uri = "bolt://localhost:7687";
        var user = "neo4j";
        var password = "12345678";
        var database = "neo4j";
        var project = "default-project";
        var connect = false;
        var dataServiceUrl = "http://localhost:8000";
        var token = string.Empty;

        da.GetData(0, ref uri);
        da.GetData(1, ref user);
        da.GetData(2, ref password);
        da.GetData(3, ref database);
        da.GetData(4, ref project);
        da.GetData(5, ref connect);
        da.GetData(6, ref dataServiceUrl);
        da.GetData(7, ref token);

        // Secrecy: never let an internalised token persist into the .gh file.
        ScrubTokenPersistentData();

        var request = new ConnectionInfo
        {
            Uri = uri,
            User = user,
            Password = password,
            Database = database,
            Project = project,
        };

        if (!connect)
        {
            CancelPendingConnection();
            _latestConnection = WithStatus(request, isConnected: false, "Connection prepared. Set Connect=true to test.");
            _latestAuth = HeartbeatResult.NotAttempted;
            Message = "Idle";
        }
        else
        {
            var requestKey = BuildRequestKey(request, dataServiceUrl, token);
            if (_connectTask is null || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
            {
                StartConnection(request, dataServiceUrl, token, requestKey);
            }

            if (_connectTask is { IsCompletedSuccessfully: true })
            {
                var result = _connectTask.Result;
                _latestConnection = result.Connection;
                _latestAuth = result.Auth;
                Message = (_latestConnection.IsConnected ? "Connected" : "Connect failed") + AuthSuffix(_latestAuth.Outcome);
                ReportAuth(_latestAuth, dataServiceUrl);
            }
            else if (_connectTask is { IsFaulted: true })
            {
                var error = _connectTask.Exception?.GetBaseException().Message ?? "Connection task failed.";
                _latestConnection = WithStatus(request, isConnected: false, error);
                _latestAuth = HeartbeatResult.NotAttempted;
                Message = "Connect failed";
            }
            else if (_connectTask is { IsCanceled: true })
            {
                _latestConnection = WithStatus(request, isConnected: false, "Connection canceled.");
                _latestAuth = HeartbeatResult.NotAttempted;
                Message = "Canceled";
            }
            else
            {
                Message = "Connecting...";
            }
        }

        // The platform token authenticates the heartbeat only — it never gates the bolt
        // connection. Both outputs are emitted regardless of the auth outcome.
        da.SetData(0, _latestConnection);
        da.SetData(1, project);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        CancelPendingConnection();
        base.RemovedFromDocument(document);
    }

    private void StartConnection(ConnectionInfo request, string dataServiceUrl, string token, string requestKey)
    {
        CancelPendingConnection();

        _activeRequestKey = requestKey;
        _latestConnection = WithStatus(request, isConnected: false, "Connecting to Neo4j...");
        _connectCts = new CancellationTokenSource();
        _connectTask = RunConnectAsync(request, dataServiceUrl, token, _connectCts.Token);

        _ = _connectTask.ContinueWith(
            _ =>
            {
                var doc = OnPingDocument();
                doc?.ScheduleSolution(1, _ => ExpireSolution(false));
            },
            TaskScheduler.Default);
    }

    private async Task<ConnectResult> RunConnectAsync(ConnectionInfo request, string dataServiceUrl, string token, CancellationToken cancellationToken)
    {
        var connection = await _connectorService.TryConnectAsync(request, cancellationToken).ConfigureAwait(false);

        // The heartbeat authenticates the platform token; skip it entirely when no token
        // is supplied so the component stays backward-compatible (pure bolt connection).
        var auth = string.IsNullOrWhiteSpace(token)
            ? HeartbeatResult.NotAttempted
            : await _heartbeatClient.CheckAsync(dataServiceUrl, token, cancellationToken).ConfigureAwait(false);

        return new ConnectResult(connection, auth);
    }

    private void ReportAuth(HeartbeatResult auth, string dataServiceUrl)
    {
        switch (auth.Outcome)
        {
            case HeartbeatOutcome.Rejected:
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ErrorMessageTemplates.ConnectorTokenRejected());
                break;
            case HeartbeatOutcome.Unreachable:
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ConnectorHeartbeatUnreachable(dataServiceUrl));
                break;
        }
    }

    private void ScrubTokenPersistentData()
    {
        if (Params.Input.Count > 7
            && Params.Input[7] is GH_PersistentParam<GH_String> tokenParam
            && tokenParam.PersistentData.DataCount > 0)
        {
            tokenParam.PersistentData.Clear();
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Remark,
                "CONNECTOR: platform token was internalised and has been cleared for security — wire it from a Panel instead.");
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

    private static string BuildRequestKey(ConnectionInfo request, string dataServiceUrl, string token)
    {
        // The token is included as a hash only — the raw secret never enters the dedup key.
        return $"{request.Uri}|{request.User}|{request.Password}|{request.Database}|{request.Project}|{dataServiceUrl}|{HashToken(token)}";
    }

    private static string HashToken(string token)
    {
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(token ?? string.Empty)));
    }

    private readonly record struct ConnectResult(ConnectionInfo Connection, HeartbeatResult Auth);

    private static ConnectionInfo WithStatus(ConnectionInfo source, bool isConnected, string status)
    {
        return new ConnectionInfo
        {
            Uri = source.Uri,
            User = source.User,
            Password = source.Password,
            Database = source.Database,
            Project = source.Project,
            IsConnected = isConnected,
            StatusMessage = status,
        };
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ConnectorComponent
{
}
#endif
