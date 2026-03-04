#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class ConnectorComponent : GH_Component
{
    private readonly INeo4jConnectorService _connectorService = new Neo4jConnectorService();
    private Task<ConnectionInfo>? _connectTask;
    private CancellationTokenSource? _connectCts;
    private string _activeRequestKey = string.Empty;
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
        : base("CONNECTOR", "CONNECTOR", "Connect to Neo4j for DG validation.", DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("24E78A17-4533-44E7-8931-1224A70A1B36");

    protected override Bitmap Icon => DgIcons.Connector24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddTextParameter("Neo4j URI", "URI", "Neo4j bolt URI", GH_ParamAccess.item, "bolt://localhost:7687");
        pManager.AddTextParameter("User", "User", "Neo4j user", GH_ParamAccess.item, "neo4j");
        pManager.AddTextParameter("Password", "Password", "Neo4j password", GH_ParamAccess.item, "12345678");
        pManager.AddTextParameter("Database", "DB", "Neo4j database", GH_ParamAccess.item, "neo4j");
        pManager.AddTextParameter("Project", "Project", "Project name", GH_ParamAccess.item, "default-project");
        pManager.AddBooleanParameter("Connect", "Go", "Set true to connect", GH_ParamAccess.item, false);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Connection", "Connection", "DG connection object", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var uri = "bolt://localhost:7687";
        var user = "neo4j";
        var password = "12345678";
        var database = "neo4j";
        var project = "default-project";
        var connect = false;

        da.GetData(0, ref uri);
        da.GetData(1, ref user);
        da.GetData(2, ref password);
        da.GetData(3, ref database);
        da.GetData(4, ref project);
        da.GetData(5, ref connect);

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
            Message = "Idle";
        }
        else
        {
            var requestKey = BuildRequestKey(request);
            if (_connectTask is null || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
            {
                StartConnection(request, requestKey);
            }

            if (_connectTask is { IsCompletedSuccessfully: true })
            {
                _latestConnection = _connectTask.Result;
                Message = _latestConnection.IsConnected ? "Connected" : "Connect failed";
            }
            else if (_connectTask is { IsFaulted: true })
            {
                var error = _connectTask.Exception?.GetBaseException().Message ?? "Connection task failed.";
                _latestConnection = WithStatus(request, isConnected: false, error);
                Message = "Connect failed";
            }
            else if (_connectTask is { IsCanceled: true })
            {
                _latestConnection = WithStatus(request, isConnected: false, "Connection canceled.");
                Message = "Canceled";
            }
            else
            {
                Message = "Connecting...";
            }
        }

        da.SetData(0, _latestConnection);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
        CancelPendingConnection();
        base.RemovedFromDocument(document);
    }

    private void StartConnection(ConnectionInfo request, string requestKey)
    {
        CancelPendingConnection();

        _activeRequestKey = requestKey;
        _latestConnection = WithStatus(request, isConnected: false, "Connecting to Neo4j...");
        _connectCts = new CancellationTokenSource();
        _connectTask = _connectorService.TryConnectAsync(request, _connectCts.Token);

        _ = _connectTask.ContinueWith(
            _ =>
            {
                var doc = OnPingDocument();
                doc?.ScheduleSolution(1, _ => ExpireSolution(false));
            },
            TaskScheduler.Default);
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

    private static string BuildRequestKey(ConnectionInfo request)
    {
        return $"{request.Uri}|{request.User}|{request.Password}|{request.Database}|{request.Project}";
    }

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
