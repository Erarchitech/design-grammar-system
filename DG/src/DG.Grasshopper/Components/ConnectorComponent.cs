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
    // Phase 1308 (WEBUI-08, D-35/D-36): the component signs in with a DG account
    // (Username + Password) and receives a connector session (dgk_) plus the
    // project scope and the Neo4j connection bundle from data-service. The
    // session is exposed on the Session output; VALIDATOR and COMPUTGRAPH
    // PUBLISH take it on their Token input. data-service base URL is a compile
    // default (ADR-825-4); a future CONN-F can re-expose it.
    private const string DataServiceUrl = "http://localhost:8000";

    private readonly INeo4jConnectorService _connectorService = new Neo4jConnectorService();
    private readonly IConnectorSessionClient _sessionClient = new ConnectorSessionClient();
    private Task<ConnectResult>? _connectTask;
    private CancellationTokenSource? _connectCts;
    private string _activeRequestKey = string.Empty;

    // The live session, kept only so it can be ended (D-32). The account password
    // is never stored in a field: it lives in the sign-in task's locals and is gone
    // when that task finishes.
    private ConnectorSessionResult? _session;
    private ConnectorSessionResult _latestAuth = ConnectorSessionResult.NotAttempted;
    private ConnectionInfo _latestConnection = new()
    {
        IsConnected = false,
        StatusMessage = "Idle",
    };

    public ConnectorComponent()
        : base("CONNECTOR", "CONNECTOR", "Sign in with your DG account and connect to Neo4j for DG validation.", DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
    {
    }

    // ADR-825-3 (renewed Phase 1308, D-36): a fresh GUID (was 3F9B1C7E-6A24-4D53-8E10-9C2A5B7D40F1).
    // The inputs changed from Token/Connect to Username/Password/Project/Connect, so
    // old canvases intentionally show a missing-component placeholder rather than
    // silently rebinding old panels by index. See docs/RELEASE-NOTES-v13.0.md.
    public override Guid ComponentGuid => new("EF2E6F2A-3450-4907-94CB-31B1240AB848");

    protected override Bitmap Icon => DgIcons.Connector24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        // Username and Password: custom non-persistent params so a typed/pasted value
        // is usable live but is never serialized into the .gh (D-38). Optional so the
        // component can show its own "not signed in" feedback instead of GH's generic
        // collect-data error.
        pManager.AddParameter(
            new NonPersistentStringParam(),
            "Username",
            "User",
            "Your DG account username. Not saved in the .gh file.",
            GH_ParamAccess.item);
        pManager.AddParameter(
            new NonPersistentStringParam(),
            "Password",
            "Pwd",
            "Your DG account password. Not saved in the .gh file.",
            GH_ParamAccess.item);
        pManager.AddTextParameter("Project", "Project", "Leave empty when you have one eligible project", GH_ParamAccess.item);
        pManager.AddBooleanParameter("Connect", "Go", "Set true to sign in and connect; set false to sign out", GH_ParamAccess.item, false);
        pManager[0].Optional = true;
        pManager[1].Optional = true;
        pManager[2].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Database", "Database", "DG connection object from CONNECTOR", GH_ParamAccess.item);
        pManager.AddTextParameter("Project", "Project", "Project the session is bound to", GH_ParamAccess.item);
        pManager.AddTextParameter("Session", "Session", "Connector session for the Token input of VALIDATOR and COMPUTGRAPH PUBLISH. Not saved in the .gh file.", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var username = string.Empty;
        var password = string.Empty;
        var project = string.Empty;
        var connect = false;

        da.GetData(0, ref username);
        da.GetData(1, ref password);
        da.GetData(2, ref project);
        da.GetData(3, ref connect);

        if (!connect)
        {
            // D-32: Connect=false ends the session so the web UI reads "off" at once.
            CancelPendingConnection();
            SignOutCurrentSession();
            _latestConnection = NotConnected("Connection prepared. Set Connect=true to sign in and connect.");
            _latestAuth = ConnectorSessionResult.NotAttempted;
            Message = "Idle";
        }
        else if (string.IsNullOrWhiteSpace(username) || string.IsNullOrEmpty(password))
        {
            CancelPendingConnection();
            SignOutCurrentSession();
            _latestConnection = NotConnected("Not signed in.");
            _latestAuth = ConnectorSessionResult.NotAttempted;
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ConnectorSignInMissing());
            Message = "Awaiting sign-in";
        }
        else
        {
            var requestKey = HashRequest(username, project, password);
            if (_connectTask is null || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
            {
                StartConnection(username, password, project, requestKey);
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
                // The exception text is not shown: nothing from the sign-in path may reach the canvas.
                _latestConnection = NotConnected("Connection task failed.");
                _latestAuth = ConnectorSessionResult.NotAttempted;
                Message = "Connect failed";
            }
            else if (_connectTask is { IsCanceled: true })
            {
                _latestConnection = NotConnected("Connection canceled.");
                _latestAuth = ConnectorSessionResult.NotAttempted;
                Message = "Canceled";
            }
            else
            {
                Message = "Connecting...";
            }
        }

        // The connection is derived entirely from the signed-in account (ADR-825-6):
        // no bundle → no live connection, and the Database output carries a
        // not-connected ConnectionInfo describing why.
        da.SetData(0, _latestConnection);
        da.SetData(1, _latestConnection.Project);
        da.SetData(2, _latestAuth.Outcome == ConnectorSessionOutcome.SignedIn ? _latestAuth.SessionToken : null);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        CancelPendingConnection();
        SignOutCurrentSession();
        base.RemovedFromDocument(document);
    }

    private void StartConnection(string username, string password, string project, string requestKey)
    {
        // A new account or project: end the previous session before opening another.
        CancelPendingConnection();
        SignOutCurrentSession();

        _activeRequestKey = requestKey;
        _latestConnection = NotConnected("Signing in...");
        _connectCts = new CancellationTokenSource();
        _connectTask = RunConnectAsync(username, password, project, _connectCts.Token);

        _ = _connectTask.ContinueWith(
            _ =>
            {
                var doc = OnPingDocument();
                doc?.ScheduleSolution(1, _ => ExpireSolution(false));
            },
            TaskScheduler.Default);
    }

    private async Task<ConnectResult> RunConnectAsync(string username, string password, string project, CancellationToken cancellationToken)
    {
        var auth = await _sessionClient
            .SignInAsync(DataServiceUrl, username, password, string.IsNullOrWhiteSpace(project) ? null : project.Trim(), cancellationToken: cancellationToken)
            .ConfigureAwait(false);

        if (auth.Outcome == ConnectorSessionOutcome.SignedIn && !string.IsNullOrEmpty(auth.SessionToken))
        {
            if (cancellationToken.IsCancellationRequested)
            {
                // Superseded or switched off while the sign-in was in flight: end the session
                // we just received instead of leaving it live until its TTL.
                await _sessionClient.SignOutAsync(DataServiceUrl, auth.SessionToken).ConfigureAwait(false);
                cancellationToken.ThrowIfCancellationRequested();
            }

            Interlocked.Exchange(ref _session, auth);
        }

        // Only a signed-in account yields a connection bundle; otherwise there is
        // nothing to connect with, so we skip the bolt attempt entirely and report
        // the reason on a not-connected ConnectionInfo.
        if (auth.Outcome != ConnectorSessionOutcome.SignedIn || auth.Bundle is not { } bundle)
        {
            // D-07: a signed-in session with no bundle means this deployment
            // (multi-user profile) doesn't hand out a direct graph connection.
            var reason = SignInMessage(auth);
            var info = new ConnectionInfo
            {
                IsConnected = false,
                StatusMessage = reason,
                Project = auth.Project ?? "default-project",
            };
            return new ConnectResult(info, auth);
        }

        var request = new ConnectionInfo
        {
            Uri = bundle.Uri ?? "bolt://localhost:7687",
            User = bundle.User ?? "neo4j",
            Password = bundle.Password ?? string.Empty,
            Database = bundle.Database ?? "neo4j",
            Project = bundle.Project ?? auth.Project ?? "default-project",
        };

        var connection = await _connectorService.TryConnectAsync(request, cancellationToken).ConfigureAwait(false);
        return new ConnectResult(connection, auth);
    }

    private static string SignInMessage(ConnectorSessionResult auth)
    {
        return auth.Outcome switch
        {
            ConnectorSessionOutcome.Rejected => ErrorMessageTemplates.ConnectorSignInRejected(),
            ConnectorSessionOutcome.Forbidden => ErrorMessageTemplates.ConnectorSignInForbidden(auth.ServerCode),
            ConnectorSessionOutcome.ProjectRequired => ErrorMessageTemplates.ConnectorProjectRequired(auth.ServerMessage),
            ConnectorSessionOutcome.Throttled => ErrorMessageTemplates.ConnectorSignInThrottled(),
            ConnectorSessionOutcome.InsecureTransport => ErrorMessageTemplates.ConnectorSignInInsecureTransport(DataServiceUrl),
            ConnectorSessionOutcome.Unreachable => ErrorMessageTemplates.ConnectorSignInUnreachable(DataServiceUrl),
            ConnectorSessionOutcome.SignedIn => ErrorMessageTemplates.ConnectorNoGraphBundle(),
            _ => ErrorMessageTemplates.ConnectorSignInMissing(),
        };
    }

    private void ReportAuth(ConnectorSessionResult auth)
    {
        switch (auth.Outcome)
        {
            case ConnectorSessionOutcome.Rejected:
            case ConnectorSessionOutcome.Forbidden:
            case ConnectorSessionOutcome.ProjectRequired:
            case ConnectorSessionOutcome.InsecureTransport:
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, SignInMessage(auth));
                break;
            case ConnectorSessionOutcome.Throttled:
            case ConnectorSessionOutcome.Unreachable:
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, SignInMessage(auth));
                break;
            case ConnectorSessionOutcome.SignedIn when auth.Bundle is null:
                // D-07: multi-user profile withholds the Neo4j bundle -- signed in,
                // but no direct graph connection is available in this deployment.
                AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, ErrorMessageTemplates.ConnectorNoGraphBundle());
                break;
        }
    }

    /// <summary>
    /// Ends the current connector session, if any, without blocking the solve (D-32).
    /// Best effort: the 8 h session TTL bounds a failure.
    /// </summary>
    private void SignOutCurrentSession()
    {
        var session = Interlocked.Exchange(ref _session, null);
        if (session?.SessionToken is not { Length: > 0 } sessionToken)
        {
            return;
        }

        _ = Task.Run(async () =>
        {
            try
            {
                await _sessionClient.SignOutAsync(DataServiceUrl, sessionToken).ConfigureAwait(false);
            }
            catch
            {
                // no-op: sign-out is best-effort and must never surface secrets.
            }
        });
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

    private static string AuthSuffix(ConnectorSessionOutcome outcome)
    {
        return outcome switch
        {
            ConnectorSessionOutcome.SignedIn => " · Signed in",
            ConnectorSessionOutcome.NotAttempted => string.Empty,
            ConnectorSessionOutcome.Unreachable => " · Sign-in unreachable",
            _ => " · Sign-in failed",
        };
    }

    private static string HashRequest(string username, string project, string password)
    {
        // The raw username, project and password never enter the dedup key — only their SHA-256 hash.
        return Convert.ToHexString(
            System.Security.Cryptography.SHA256.HashData(
                System.Text.Encoding.UTF8.GetBytes($"{username}\u0000{project}\u0000{password}")));
    }

    private readonly record struct ConnectResult(ConnectionInfo Connection, ConnectorSessionResult Auth);
}
#else
namespace DG.Grasshopper.Components;

public sealed class ConnectorComponent
{
}
#endif
