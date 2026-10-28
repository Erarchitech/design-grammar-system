#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Services;
using DG.Grasshopper.Mapping;
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
    // default (ADR-825-4) unless the Server input names another DG server (quick 261028-vm9).
    // With a remote server, or when the server hands out no Neo4j bundle (multi-user profile),
    // graph reads go through the server's /connector-graph route instead of Bolt.
    private string _dataServiceUrl = DataServiceRequestAuth.DefaultServerUrl;
    // The server the live session was minted on: it must be ended there even after the input changes.
    private string _sessionServerUrl = DataServiceRequestAuth.DefaultServerUrl;
    private string _mappingServerUrl = string.Empty;

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

    /// <summary>Phase 1303-15: why the graph connection failed (the Neo4j driver's message; never credentials),
    /// read by the canvas bridge's property-check status so "Connect failed" can be diagnosed remotely.</summary>
    internal string ConnectionStatus => _latestConnection.StatusMessage;

    internal bool IsGraphConnected => _latestConnection.IsConnected;

    // Phase 1303 (owner amendment 2026-10-18): after sign-in CONNECTOR proposes the mapping
    // of this definition to DG automatically — no mapping component and no wiring.
    private MappingAutoRunner? _mapping;

    /// <summary>The automatic mapping of this definition (plan 1303-10: the canvas bridge starts it and reads its status).</summary>
    internal MappingAutoRunner? Mapping => _mapping;

    public ConnectorComponent()
        : base("CONNECTOR", "CONNECTOR", "Sign in with your DG account (local or on a DG server) and connect to the DG graph for validation.", DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
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
        pManager.AddBooleanParameter(
            "AutoMap",
            "Map",
            "Propose the mapping of this definition to DG classes and properties automatically after sign-in. Questions are answered in the DG Web UI → Projects → Mapping.",
            GH_ParamAccess.item,
            true);
        pManager.AddTextParameter(
            "Server",
            "Server",
            "DG server address, for example https://dg.example.com. Leave empty for the DG on this computer (http://localhost:8000). Wire the Server output to VALIDATOR and COMPUTGRAPH PUBLISH DataServiceUrl.",
            GH_ParamAccess.item,
            string.Empty);
        pManager[0].Optional = true;
        pManager[1].Optional = true;
        pManager[2].Optional = true;
        pManager[4].Optional = true;
        pManager[5].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Database", "Database", "DG connection object from CONNECTOR", GH_ParamAccess.item);
        pManager.AddTextParameter("Project", "Project", "Project the session is bound to", GH_ParamAccess.item);
        pManager.AddTextParameter("Session", "Session", "Connector session for the Token input of VALIDATOR and COMPUTGRAPH PUBLISH. Not saved in the .gh file.", GH_ParamAccess.item);
        pManager.AddTextParameter("Mapping", "Mapping", "Automatic mapping of this definition: elements, sliders, open questions and where to answer them.", GH_ParamAccess.item);
        pManager.AddGeometryParameter("ByClass", "ByClass", "Applied mapping: branch {k} holds the geometry mapped to ClassNames[k], in canvas order. Feed OBJECT STATE Geometry.", GH_ParamAccess.tree);
        pManager.AddTextParameter("ClassNames", "ClassNames", "Classes of the applied mapping, aligned with ByClass branches.", GH_ParamAccess.list);
        pManager.AddGenericParameter("ClassObjects", "ClassObjects", "DG classes aligned with ByClass branches. Feed OBJECT STATE Object.", GH_ParamAccess.list);
        pManager.AddTextParameter("Sliders", "Sliders", "Named sliders and the DG property proposed or confirmed for each.", GH_ParamAccess.list);
        pManager.AddTextParameter("Server", "Server", "The DG server address in use. Wire it to the DataServiceUrl input of VALIDATOR and COMPUTGRAPH PUBLISH.", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var username = string.Empty;
        var password = string.Empty;
        var project = string.Empty;
        var connect = false;
        var autoMap = true;
        var server = string.Empty;

        da.GetData(0, ref username);
        da.GetData(1, ref password);
        da.GetData(2, ref project);
        da.GetData(3, ref connect);
        da.GetData(4, ref autoMap);
        da.GetData(5, ref server);
        _dataServiceUrl = DataServiceRequestAuth.NormalizeServerUrl(server);

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
            var requestKey = HashRequest(username, project, password, _dataServiceUrl);
            if (_connectTask is null || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
            {
                StartConnection(username, password, project, _dataServiceUrl, requestKey);
            }

            if (_connectTask is { Status: TaskStatus.RanToCompletion })
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
        var sessionToken = _latestAuth.Outcome == ConnectorSessionOutcome.SignedIn ? _latestAuth.SessionToken : null;
        da.SetData(2, sessionToken);

        // Automatic mapping (Phase 1303): reads the canvas after the solution settles; never
        // blocks this solve. The token stays inside the plugin (Authorization header only).
        if (_mapping is not null && !string.Equals(_mappingServerUrl, _dataServiceUrl, StringComparison.Ordinal))
        {
            _mapping.Dispose();
            _mapping = null;
        }

        _mappingServerUrl = _dataServiceUrl;
        _mapping ??= new MappingAutoRunner(this, _dataServiceUrl);
        _mapping.Configure(OnPingDocument(), sessionToken, _latestConnection.Project ?? _latestAuth.Project, autoMap);
        var mapping = _mapping.Outputs;
        da.SetData(3, mapping.Summary);
        da.SetDataTree(4, mapping.ByClass);
        da.SetDataList(5, mapping.ClassNames);
        da.SetDataList(6, mapping.ClassObjects);
        da.SetDataList(7, mapping.Sliders);
        da.SetData(8, _dataServiceUrl);
        if (sessionToken is not null)
        {
            Message += mapping.MessageSuffix;
        }
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        _mapping?.Dispose();
        _mapping = null;
        CancelPendingConnection();
        SignOutCurrentSession();
        base.RemovedFromDocument(document);
    }

    public override void DocumentContextChanged(GH_Document document, GH_DocumentContext context)
    {
        if (context is GH_DocumentContext.Close or GH_DocumentContext.Unloaded)
        {
            _mapping?.Dispose();
            _mapping = null;
        }

        base.DocumentContextChanged(document, context);
    }

    private void StartConnection(string username, string password, string project, string dataServiceUrl, string requestKey)
    {
        // A new account or project: end the previous session before opening another.
        CancelPendingConnection();
        SignOutCurrentSession();

        _activeRequestKey = requestKey;
        _latestConnection = NotConnected("Signing in...");
        _connectCts = new CancellationTokenSource();
        _connectTask = RunConnectAsync(username, password, project, dataServiceUrl, _connectCts.Token);

        _ = _connectTask.ContinueWith(
            _ =>
            {
                var doc = OnPingDocument();
                doc?.ScheduleSolution(1, _ => ExpireSolution(false));
            },
            TaskScheduler.Default);
    }

    private async Task<ConnectResult> RunConnectAsync(string username, string password, string project, string dataServiceUrl, CancellationToken cancellationToken)
    {
        var auth = await _sessionClient
            .SignInAsync(dataServiceUrl, username, password, string.IsNullOrWhiteSpace(project) ? null : project.Trim(), cancellationToken: cancellationToken)
            .ConfigureAwait(false);

        if (auth.Outcome == ConnectorSessionOutcome.SignedIn && !string.IsNullOrEmpty(auth.SessionToken))
        {
            if (cancellationToken.IsCancellationRequested)
            {
                // Superseded or switched off while the sign-in was in flight: end the session
                // we just received instead of leaving it live until its TTL.
                await _sessionClient.SignOutAsync(dataServiceUrl, auth.SessionToken).ConfigureAwait(false);
                cancellationToken.ThrowIfCancellationRequested();
            }

            _sessionServerUrl = dataServiceUrl;
            Interlocked.Exchange(ref _session, auth);
        }

        // Only a signed-in account can read the graph; otherwise there is nothing to
        // connect with, so we report the reason on a not-connected ConnectionInfo.
        if (auth.Outcome != ConnectorSessionOutcome.SignedIn)
        {
            var reason = SignInMessage(auth, dataServiceUrl);
            var info = new ConnectionInfo
            {
                IsConnected = false,
                StatusMessage = reason,
                Project = auth.Project ?? "default-project",
            };
            return new ConnectResult(info, auth);
        }

        // Server mode (quick 261028-vm9): a multi-user server withholds the Neo4j bundle (D-07), and a
        // remote server's bundle points at its own loopback. Either way the graph is read through the
        // server's HTTPS graph API with the connector session, and no Bolt connection is made.
        if (auth.Bundle is not { } bundle || DataServiceRequestAuth.IsRemoteServer(dataServiceUrl))
        {
            var serverRequest = new ConnectionInfo
            {
                Project = auth.Project ?? "default-project",
                GraphApiUrl = dataServiceUrl,
                GraphApiToken = auth.SessionToken,
            };

            var serverConnection = await _connectorService.TryConnectAsync(serverRequest, cancellationToken).ConfigureAwait(false);
            return new ConnectResult(serverConnection, auth);
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

    private static string SignInMessage(ConnectorSessionResult auth, string dataServiceUrl)
    {
        return auth.Outcome switch
        {
            ConnectorSessionOutcome.Rejected => ErrorMessageTemplates.ConnectorSignInRejected(),
            ConnectorSessionOutcome.Forbidden => ErrorMessageTemplates.ConnectorSignInForbidden(auth.ServerCode),
            ConnectorSessionOutcome.ProjectRequired => ErrorMessageTemplates.ConnectorProjectRequired(auth.ServerMessage),
            ConnectorSessionOutcome.Throttled => ErrorMessageTemplates.ConnectorSignInThrottled(),
            ConnectorSessionOutcome.InsecureTransport => ErrorMessageTemplates.ConnectorSignInInsecureTransport(dataServiceUrl),
            ConnectorSessionOutcome.Unreachable => ErrorMessageTemplates.ConnectorSignInUnreachable(dataServiceUrl),
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
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, SignInMessage(auth, _dataServiceUrl));
                break;
            case ConnectorSessionOutcome.Throttled:
            case ConnectorSessionOutcome.Unreachable:
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, SignInMessage(auth, _dataServiceUrl));
                break;
            case ConnectorSessionOutcome.SignedIn when !_latestConnection.IsConnected:
                // Signed in, but the graph read over the server failed: show why (the safe text of GraphApiException).
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, _latestConnection.StatusMessage);
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

        var sessionUrl = _sessionServerUrl;
        _ = Task.Run(async () =>
        {
            try
            {
                await _sessionClient.SignOutAsync(sessionUrl, sessionToken).ConfigureAwait(false);
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

    private static string HashRequest(string username, string project, string password, string server)
    {
        // The raw username, project and password never enter the dedup key — only their SHA-256 hash.
        return DG.Core.Compat.DgCompat.ToHex(
            DG.Core.Compat.DgCompat.Sha256(
                System.Text.Encoding.UTF8.GetBytes($"{username}\u0000{project}\u0000{password}\u0000{server}")));
    }

    private readonly record struct ConnectResult(ConnectionInfo Connection, ConnectorSessionResult Auth);
}
#else
namespace DG.Grasshopper.Components;

public sealed class ConnectorComponent
{
}
#endif
