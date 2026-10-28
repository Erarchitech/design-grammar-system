using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using DG.Core.Models;
using Neo4j.Driver;

namespace DG.Core.Data;

/// <summary>One result row, read by column name. Backed by a Bolt record or a JSON row from the data-service.</summary>
public interface IGraphRecord
{
    string? GetString(string name);

    int GetInt(string name);

    IReadOnlyList<string> GetStringList(string name);

    bool GetBool(string name);
}

/// <summary>
/// One read session against the graph. The repositories issue their named queries through it and do not
/// care whether the rows come from Neo4j over Bolt (trusted-local profile) or from the data-service
/// <c>/connector-graph</c> route over HTTPS (multi-user profile, where the Neo4j bundle is withheld).
/// Dispose is synchronous on purpose (see <see cref="Neo4jConnectorService"/>).
/// </summary>
public interface IGraphQuerySession : IDisposable
{
    /// <param name="queryId">The name the data-service knows the statement by (<c>connector_graph.QUERIES</c>).</param>
    /// <param name="cypher">The same statement, run directly in Bolt mode; never sent to the data-service.</param>
    /// <param name="parameters">Extra bound parameters; <c>project</c> is always taken from the connection.</param>
    Task<IReadOnlyList<IGraphRecord>> QueryAsync(
        string queryId,
        string cypher,
        IReadOnlyDictionary<string, object?>? parameters,
        CancellationToken cancellationToken);
}

public static class GraphQuerySession
{
    private static readonly TimeSpan QueryTimeout = TimeSpan.FromSeconds(20);

    /// <summary>Opens the read path the connection calls for: the HTTPS graph API when it carries a
    /// <see cref="ConnectionInfo.GraphApiUrl"/>, Bolt otherwise.</summary>
    public static IGraphQuerySession Open(ConnectionInfo connection)
    {
        return connection.UsesGraphApi
            ? new DataServiceGraphSession(connection)
            : new BoltGraphSession(connection);
    }

    private sealed class BoltGraphSession : IGraphQuerySession
    {
        private readonly ConnectionInfo _connection;
        private readonly IDriver _driver;
        private readonly IAsyncSession _session;

        public BoltGraphSession(ConnectionInfo connection)
        {
            _connection = connection;
            _driver = GraphDatabase.Driver(connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
            _session = _driver.AsyncSession(options => options.WithDatabase(connection.Database));
        }

        public async Task<IReadOnlyList<IGraphRecord>> QueryAsync(
            string queryId,
            string cypher,
            IReadOnlyDictionary<string, object?>? parameters,
            CancellationToken cancellationToken)
        {
            var bound = new Dictionary<string, object?>(StringComparer.Ordinal) { ["project"] = _connection.Project };
            if (parameters is not null)
            {
                foreach (var pair in parameters)
                {
                    bound[pair.Key] = pair.Value;
                }
            }

            var cursor = await _session
                .RunAsync(cypher, bound!)
                .WaitAsync(QueryTimeout, cancellationToken);

            var rows = await cursor
                .ToListAsync(record => (IGraphRecord)new BoltGraphRecord(record))
                .WaitAsync(QueryTimeout, cancellationToken);
            return rows;
        }

        public void Dispose()
        {
            _session.Dispose();
            _driver.Dispose();
        }
    }

    private sealed class DataServiceGraphSession : IGraphQuerySession
    {
        private static readonly HttpClient Http = new(new HttpClientHandler { UseCookies = false });

        private readonly ConnectionInfo _connection;

        public DataServiceGraphSession(ConnectionInfo connection)
        {
            _connection = connection;
        }

        public async Task<IReadOnlyList<IGraphRecord>> QueryAsync(
            string queryId,
            string cypher,
            IReadOnlyDictionary<string, object?>? parameters,
            CancellationToken cancellationToken)
        {
            var baseUrl = _connection.GraphApiUrl!.Trim().TrimEnd('/');
            if (DataServiceRequestAuth.IsInsecureRemoteTransport(baseUrl))
            {
                throw new GraphApiException(
                    "The DG server address uses plain http. Use an https:// address; the session token is never sent unencrypted.");
            }

            var url = $"{baseUrl}/connector-graph/{Uri.EscapeDataString(_connection.Project)}/{Uri.EscapeDataString(queryId)}";
            if (parameters is not null && parameters.TryGetValue("runId", out var runId) && runId is string runIdText)
            {
                url += $"?runId={Uri.EscapeDataString(runIdText)}";
            }

            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            if (!DataServiceRequestAuth.TryApplyConnectorToken(request, _connection.GraphApiToken, out _))
            {
                throw new GraphApiException("No connector session. Set Connect=true to sign in.");
            }

            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(QueryTimeout);

            HttpResponseMessage response;
            try
            {
                response = await Http.SendAsync(request, timeout.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
            {
                throw new GraphApiException("The DG server did not answer in time.");
            }
            catch (HttpRequestException)
            {
                throw new GraphApiException("The DG server could not be reached.");
            }

            using (response)
            {
                var body = await response.Content.ReadAsStringAsync(timeout.Token).ConfigureAwait(false);
                if (!response.IsSuccessStatusCode)
                {
                    throw new GraphApiException(Describe(response.StatusCode, body));
                }

                return Parse(body);
            }
        }

        public void Dispose()
        {
        }

        internal static IReadOnlyList<IGraphRecord> Parse(string body)
        {
            try
            {
                using var document = JsonDocument.Parse(body);
                if (!document.RootElement.TryGetProperty("rows", out var rows) || rows.ValueKind != JsonValueKind.Array)
                {
                    throw new GraphApiException("The DG server answered without rows.");
                }

                var records = new List<IGraphRecord>(rows.GetArrayLength());
                foreach (var row in rows.EnumerateArray())
                {
                    // Clone: the document is disposed when this method returns.
                    records.Add(new JsonGraphRecord(row.Clone()));
                }

                return records;
            }
            catch (JsonException)
            {
                throw new GraphApiException("The DG server answered with something that is not JSON.");
            }
        }

        private static string Describe(HttpStatusCode status, string body)
        {
            var code = ReadCode(body);
            return status switch
            {
                HttpStatusCode.Unauthorized => "The DG session ended or expired. Set Connect=false, then true to sign in again.",
                HttpStatusCode.Forbidden => $"The DG server refused the graph read for this project{Suffix(code)}.",
                HttpStatusCode.NotFound when code == "GRAPH_QUERY_NOT_FOUND" =>
                    "The DG server does not know this graph query. Update the server to a version with /connector-graph.",
                HttpStatusCode.NotFound => "The DG server has no /connector-graph route. Update the server.",
                _ => $"The DG server could not read the graph (HTTP {(int)status}){Suffix(code)}.",
            };
        }

        private static string Suffix(string? code) => string.IsNullOrEmpty(code) ? string.Empty : $" [{code}]";

        private static string? ReadCode(string body)
        {
            try
            {
                using var document = JsonDocument.Parse(body);
                if (document.RootElement.TryGetProperty("detail", out var detail)
                    && detail.ValueKind == JsonValueKind.Object
                    && detail.TryGetProperty("code", out var code)
                    && code.ValueKind == JsonValueKind.String)
                {
                    return code.GetString();
                }
            }
            catch (JsonException)
            {
            }

            return null;
        }
    }

    private sealed class BoltGraphRecord : IGraphRecord
    {
        private readonly IRecord _record;

        public BoltGraphRecord(IRecord record)
        {
            _record = record;
        }

        public string? GetString(string name) => _record[name].As<string?>();

        public int GetInt(string name) => _record[name].As<int>();

        public bool GetBool(string name) => _record[name].As<bool>();

        public IReadOnlyList<string> GetStringList(string name) => _record[name].As<List<string>?>() ?? new List<string>();
    }

    internal sealed class JsonGraphRecord : IGraphRecord
    {
        private readonly JsonElement _row;

        public JsonGraphRecord(JsonElement row)
        {
            _row = row;
        }

        public string? GetString(string name)
        {
            if (!_row.TryGetProperty(name, out var value))
            {
                return null;
            }

            return value.ValueKind switch
            {
                JsonValueKind.Null or JsonValueKind.Undefined => null,
                JsonValueKind.String => value.GetString(),
                _ => value.GetRawText(),
            };
        }

        public int GetInt(string name)
        {
            return _row.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Number && value.TryGetInt64(out var number)
                ? (int)number
                : 0;
        }

        public bool GetBool(string name)
        {
            return _row.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.True;
        }

        public IReadOnlyList<string> GetStringList(string name)
        {
            if (!_row.TryGetProperty(name, out var value) || value.ValueKind != JsonValueKind.Array)
            {
                return Array.Empty<string>();
            }

            var items = new List<string>(value.GetArrayLength());
            foreach (var item in value.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String && item.GetString() is { } text)
                {
                    items.Add(text);
                }
            }

            return items;
        }
    }

    internal static IReadOnlyList<IGraphRecord> ParseForTesting(string body) => DataServiceGraphSession.Parse(body);
}

/// <summary>A graph read over the data-service failed. The message is safe to show: no token, URL or credential.</summary>
public sealed class GraphApiException : Exception
{
    public GraphApiException(string message)
        : base(message)
    {
    }
}
