using System.Net.Http;
using System.Text;
using System.Text.Json;
using DG.Core.Data;

namespace DG.Core.Mapping;

/// <summary>Mapping state of one element as the session reports it.</summary>
public sealed record MappingElementState(string State, IReadOnlyList<string> RoleLabels);

/// <summary>Mapping state of one slider: state and the proposed or confirmed property.</summary>
public sealed record MappingParameterState(string NativeId, string Name, string State, string? PropertyLabel, string? PropertyIri);

/// <summary>
/// One proposed canvas component and the temporary tag CONNECTOR draws around it (plan 1303-10):
/// <see cref="ComponentId"/> is the 32-hex GH InstanceGuid of the stream source, calculation output or slider.
/// </summary>
public sealed record MappingCanvasTag(string ComponentId, string State, string Text);

/// <summary>The parts of a mapping session CONNECTOR shows on the canvas.</summary>
public sealed class MappingSessionState
{
    public string SessionId { get; init; } = string.Empty;

    /// <summary>The GH document key the session was read from (null for imported Revit sessions).</summary>
    public string? Document { get; init; }

    /// <summary>Tags for the components of open proposals and of given answers, proposals first.</summary>
    public IReadOnlyList<MappingCanvasTag> Tags { get; init; } = Array.Empty<MappingCanvasTag>();

    public int Total { get; init; }

    public int OpenQuestions { get; init; }

    public IReadOnlyDictionary<string, int> Counts { get; init; } = new Dictionary<string, int>();

    public IReadOnlyDictionary<string, MappingElementState> Elements { get; init; } = new Dictionary<string, MappingElementState>();

    public IReadOnlyList<MappingParameterState> Parameters { get; init; } = Array.Empty<MappingParameterState>();

    public IReadOnlyList<MappingMeasureState> Measures { get; init; } = Array.Empty<MappingMeasureState>();

    /// <summary>LLM proposal status of the session (ok / empty / unavailable), when one was asked for.</summary>
    public string? LlmStatus { get; init; }

    /// <summary>Server revision of the draft (legacy sessions fall back to a display hash).</summary>
    public string Revision { get; init; } = string.Empty;

    public string? AppliedAt { get; init; }

    public IReadOnlyList<MappingBatch> Batches { get; init; } = Array.Empty<MappingBatch>();
}

/// <summary>An explicitly confirmed immutable selection; queued is not proof of CAD delivery.</summary>
public sealed record MappingBatch(string BatchId, MappingApplyResult Payload, string DeliveryState);

public sealed record MappingDeliveryReceipt(string State, int Written, int Skipped);

/// <summary>A rule bound to a class, a property and the calculation output that carries it (D-37).</summary>
public sealed record MappingRuleBinding(string RuleId, string ClassIri, string PropertyIri, string MeasureId, string Stream);

/// <summary>A calculation output and the DG property it carries.</summary>
public sealed record MappingMeasureState(string NativeId, string Name, string State, string? PropertyLabel, string? PropertyIri, string? Stream);

/// <summary>Applied mapping: classes per element, streams, DG parameters, measures and rule bindings.</summary>
public sealed class MappingApplyResult
{
    public IReadOnlyDictionary<string, IReadOnlyList<string>> RolesByElement { get; init; } = new Dictionary<string, IReadOnlyList<string>>();

    public IReadOnlyDictionary<string, string> ElementStreams { get; init; } = new Dictionary<string, string>();

    public IReadOnlyList<MappingParameterState> Parameters { get; init; } = Array.Empty<MappingParameterState>();

    public IReadOnlyList<MappingMeasureState> Measures { get; init; } = Array.Empty<MappingMeasureState>();

    public IReadOnlyList<MappingRuleBinding> Bindings { get; init; } = Array.Empty<MappingRuleBinding>();
}

/// <summary>Outcome of one call: the parsed value, or the HTTP status and DG error code.</summary>
public sealed record MappingCallResult<T>(T? Value, int Status, string? ErrorCode)
    where T : class
{
    public bool Ok => Value is not null;
}

/// <summary>
/// HTTP client for the mapping routes (<c>/mapping/sessions</c>, <c>/{id}</c>, <c>/{id}/apply</c>).
/// The connector session (<c>dgk_</c>) goes only into the Authorization header, never into a
/// field, URI, log or exception message (as <see cref="ConnectorSessionClient"/>).
/// No Grasshopper SDK dependency, so it is testable from DG.Tests.
/// </summary>
public sealed class MappingSessionClient
{
    // Creating a session can include one LLM proposal (D-37), which takes longer than a read.
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(150);
    private readonly HttpClient _httpClient;

    public MappingSessionClient(HttpMessageHandler? handler = null)
    {
        _httpClient = handler is null ? new HttpClient() : new HttpClient(handler);
        _httpClient.Timeout = RequestTimeout;
    }

    public Task<MappingCallResult<MappingSessionState>> CreateAsync(
        string dataServiceUrl, string? token, string requestJson, CancellationToken cancellationToken = default) =>
        SendAsync(HttpMethod.Post, $"{Normalize(dataServiceUrl)}/mapping/sessions", token, requestJson, ParseSession, cancellationToken);

    public Task<MappingCallResult<MappingSessionState>> GetAsync(
        string dataServiceUrl, string? token, string project, string sessionId, CancellationToken cancellationToken = default) =>
        SendAsync(
            HttpMethod.Get,
            $"{Normalize(dataServiceUrl)}/mapping/sessions/{Uri.EscapeDataString(sessionId)}?project={Uri.EscapeDataString(project)}",
            token,
            null,
            ParseSession,
            cancellationToken);

    public Task<MappingCallResult<MappingBatch>> AcknowledgeAsync(
        string dataServiceUrl, string? token, string project, string sessionId, string batchId,
        MappingDeliveryReceipt delivery, CancellationToken cancellationToken = default) =>
        SendAsync(
            HttpMethod.Post,
            $"{Normalize(dataServiceUrl)}/mapping/sessions/{Uri.EscapeDataString(sessionId)}/apply",
            token,
            JsonSerializer.Serialize(new
            {
                project, batchId,
                delivery = new { state = delivery.State, written = delivery.Written, skipped = delivery.Skipped },
            }),
            ParseBatch,
            cancellationToken);

    private async Task<MappingCallResult<T>> SendAsync<T>(
        HttpMethod method, string url, string? token, string? body, Func<string, T> parse, CancellationToken cancellationToken)
        where T : class
    {
        try
        {
            using var request = new HttpRequestMessage(method, url);
            if (!DataServiceRequestAuth.TryApplyConnectorToken(request, token, out _))
            {
                return new MappingCallResult<T>(null, 0, "SIGN_IN_REQUIRED");
            }

            if (body is not null)
            {
                request.Content = new StringContent(body, Encoding.UTF8, "application/json");
            }

            using var response = await _httpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
            var text = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
            if (!response.IsSuccessStatusCode)
            {
                return new MappingCallResult<T>(null, (int)response.StatusCode, ErrorCode(text));
            }

            return new MappingCallResult<T>(parse(text), (int)response.StatusCode, null);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            // Network failure, timeout or malformed response; message-free by design.
            return new MappingCallResult<T>(null, 0, "UNREACHABLE");
        }
    }

    public static MappingSessionState ParseSession(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var counts = new Dictionary<string, int>(StringComparer.Ordinal);
        var total = 0;
        var open = 0;
        if (root.TryGetProperty("summary", out var summary) && summary.ValueKind == JsonValueKind.Object)
        {
            foreach (var p in summary.EnumerateObject())
            {
                if (p.Value.ValueKind == JsonValueKind.Number && p.Value.TryGetInt32(out var n))
                {
                    counts[p.Name] = n;
                }
            }

            counts.TryGetValue("total", out total);
            counts.TryGetValue("openQuestions", out open);
        }

        var elements = new Dictionary<string, MappingElementState>(StringComparer.Ordinal);
        var revision = new StringBuilder();
        if (root.TryGetProperty("elements", out var els) && els.ValueKind == JsonValueKind.Array)
        {
            foreach (var el in els.EnumerateArray())
            {
                var id = Text(el, "nativeId");
                if (id is null)
                {
                    continue;
                }

                var state = Text(el, "state") ?? "unmapped";
                var labels = new List<string>();
                if (el.TryGetProperty("roles", out var roles) && roles.ValueKind == JsonValueKind.Array)
                {
                    foreach (var r in roles.EnumerateArray())
                    {
                        var label = Text(r, "label") ?? LocalName(Text(r, "classIri"));
                        if (!string.IsNullOrEmpty(label))
                        {
                            labels.Add(label);
                        }
                    }
                }

                elements[id] = new MappingElementState(state, labels);
                revision.Append(id).Append('=').Append(state).Append(':').Append(string.Join("+", labels)).Append(';');
            }
        }

        var parameters = ParseParameters(root);
        foreach (var p in parameters)
        {
            revision.Append(p.NativeId).Append('=').Append(p.State).Append(':').Append(p.PropertyIri).Append(';');
        }

        var measures = ParseMeasures(root, "measures");
        foreach (var m in measures)
        {
            revision.Append(m.NativeId).Append('=').Append(m.State).Append(':').Append(m.PropertyIri).Append(';');
        }

        string? llm = null;
        if (root.TryGetProperty("llm", out var llmBlock) && llmBlock.ValueKind == JsonValueKind.Object)
        {
            llm = Text(llmBlock, "status");
        }

        var tags = ParseTags(root);
        foreach (var t in tags)
        {
            revision.Append(t.ComponentId).Append('#').Append(t.Text).Append(';');
        }

        var batches = new List<MappingBatch>();
        if (root.TryGetProperty("batches", out var bs) && bs.ValueKind == JsonValueKind.Array)
        {
            batches.AddRange(bs.EnumerateArray().Select(ParseBatch));
        }

        return new MappingSessionState
        {
            SessionId = Text(root, "sessionId") ?? string.Empty,
            AppliedAt = Text(root, "appliedAt"),
            Batches = batches,
            Document = Text(root, "document"),
            Tags = tags,
            Total = total,
            OpenQuestions = open,
            Counts = counts,
            Elements = elements,
            Parameters = parameters,
            Measures = measures,
            LlmStatus = llm,
            Revision = Text(root, "revision") ?? Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(Encoding.UTF8.GetBytes(revision.ToString())), 0, 8),
        };
    }

    /// <summary>The tag text: state mark, component name, proposal (and alternatives while ambiguous).</summary>
    public static string TagText(string state, string name, string? proposal, IReadOnlyList<string> alternatives)
    {
        var mark = state switch
        {
            "ambiguous" => "DG ?",
            "suggested" => "DG ·",
            "confirmed" => "DG ✓",
            "auto" => "DG ↺",
            _ => "DG –",
        };
        var target = proposal is null
            ? "—"
            : state == "ambiguous" && alternatives.Count > 0 ? $"{proposal} | {string.Join(" | ", alternatives)}" : proposal;
        return $"{mark} {name} → {target}";
    }

    private static List<MappingCanvasTag> ParseTags(JsonElement root)
    {
        var tags = new List<MappingCanvasTag>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var (key, fallbackState) in new[] { ("questions", (string?)null), ("answers", "confirmed") })
        {
            if (!root.TryGetProperty(key, out var list) || list.ValueKind != JsonValueKind.Array)
            {
                continue;
            }

            foreach (var entry in list.EnumerateArray())
            {
                if (!entry.TryGetProperty("items", out var items) || items.ValueKind != JsonValueKind.Array)
                {
                    continue;
                }

                foreach (var item in items.EnumerateArray())
                {
                    var id = Text(item, "componentId");
                    if (string.IsNullOrEmpty(id) || !seen.Add(id + "|" + Text(item, "itemId")))
                    {
                        continue;
                    }

                    var state = Text(item, "state") ?? fallbackState ?? "suggested";
                    string? proposal = null;
                    if (item.TryGetProperty("proposal", out var prop) && prop.ValueKind == JsonValueKind.Object)
                    {
                        proposal = Text(prop, "label") ?? LocalName(Text(prop, "iri"));
                    }

                    var alternatives = new List<string>();
                    if (item.TryGetProperty("alternatives", out var alts) && alts.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var alt in alts.EnumerateArray())
                        {
                            var label = Text(alt, "label") ?? LocalName(Text(alt, "iri"));
                            if (!string.IsNullOrEmpty(label))
                            {
                                alternatives.Add(label);
                            }
                        }
                    }

                    tags.Add(new MappingCanvasTag(id, state, TagText(state, Text(item, "name") ?? "?", proposal, alternatives)));
                }
            }
        }

        return tags;
    }

    public static MappingBatch ParseBatch(string json)
    {
        using var doc = JsonDocument.Parse(json);
        return ParseBatch(doc.RootElement);
    }

    private static MappingBatch ParseBatch(JsonElement root)
    {
        var id = Text(root, "batchId");
        var state = root.TryGetProperty("delivery", out var delivery) ? Text(delivery, "state") : null;
        if (string.IsNullOrWhiteSpace(id) || state is not ("queued" or "written" or "failed")
            || !root.TryGetProperty("payload", out var payload) || payload.ValueKind != JsonValueKind.Object)
        {
            throw new FormatException("Invalid mapping batch");
        }

        foreach (var field in new[] { "elements", "parameters", "measures", "bindings" })
        {
            if (!payload.TryGetProperty(field, out var rows))
            {
                if (field == "elements") throw new FormatException("Missing mapping elements");
                continue;
            }
            if (rows.ValueKind != JsonValueKind.Array) throw new FormatException("Invalid mapping rows");
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var row in rows.EnumerateArray())
            {
                if (row.ValueKind != JsonValueKind.Object) throw new FormatException("Invalid mapping row");
                var key = field == "bindings"
                    ? string.Join("|", new[] { "ruleId", "classIri", "propertyIri", "measureId", "stream" }.Select(k => Text(row, k)))
                    : Text(row, "nativeId");
                if (string.IsNullOrWhiteSpace(key) || !seen.Add(key)) throw new FormatException("Repeated or missing mapping identity");
                if (field == "elements")
                {
                    if (!row.TryGetProperty("roles", out var rs) || rs.ValueKind != JsonValueKind.Array || rs.GetArrayLength() == 0
                        || rs.EnumerateArray().Any(r => r.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(r.GetString()))
                        || rs.EnumerateArray().Select(r => r.GetString()).Distinct(StringComparer.Ordinal).Count() != rs.GetArrayLength())
                        throw new FormatException("Invalid committed roles");
                }
                if (field == "measures" && string.IsNullOrWhiteSpace(Text(row, "propertyIri")))
                    throw new FormatException("Missing committed property");
                if (field == "bindings" && new[] { "ruleId", "classIri", "propertyIri", "measureId", "stream" }
                    .Any(k => string.IsNullOrWhiteSpace(Text(row, k)))) throw new FormatException("Invalid committed binding");
            }
        }
        var parsed = ParseApply(payload.GetRawText());
        if (!payload.TryGetProperty("applied", out var count) || count.ValueKind != JsonValueKind.Number || !count.TryGetInt32(out var n)
            || n < 0 || n != parsed.RolesByElement.Count)
        {
            throw new FormatException("Invalid mapping batch count");
        }

        return new MappingBatch(id, parsed, state);
    }

    public static MappingApplyResult ParseApply(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var roles = new Dictionary<string, IReadOnlyList<string>>(StringComparer.Ordinal);
        var streams = new Dictionary<string, string>(StringComparer.Ordinal);
        if (root.TryGetProperty("elements", out var els) && els.ValueKind == JsonValueKind.Array)
        {
            foreach (var el in els.EnumerateArray())
            {
                var id = Text(el, "nativeId");
                if (id is null || !el.TryGetProperty("roles", out var rs) || rs.ValueKind != JsonValueKind.Array)
                {
                    continue;
                }

                roles[id] = rs.EnumerateArray()
                    .Where(r => r.ValueKind == JsonValueKind.String)
                    .Select(r => r.GetString()!)
                    .ToList();
                if (Text(el, "stream") is { } stream)
                {
                    streams[id] = stream;
                }
            }
        }

        var parameters = new List<MappingParameterState>();
        if (root.TryGetProperty("parameters", out var ps) && ps.ValueKind == JsonValueKind.Array)
        {
            foreach (var p in ps.EnumerateArray())
            {
                parameters.Add(new MappingParameterState(Text(p, "nativeId") ?? string.Empty, Text(p, "name") ?? string.Empty, "applied", "DG parameter", null));
            }
        }

        var bindings = new List<MappingRuleBinding>();
        if (root.TryGetProperty("bindings", out var bs) && bs.ValueKind == JsonValueKind.Array)
        {
            foreach (var b in bs.EnumerateArray())
            {
                var rule = Text(b, "ruleId");
                var cls = Text(b, "classIri");
                var prop = Text(b, "propertyIri");
                var measure = Text(b, "measureId");
                if (rule is not null && cls is not null && prop is not null && measure is not null)
                {
                    bindings.Add(new MappingRuleBinding(rule, cls, prop, measure, Text(b, "stream") ?? string.Empty));
                }
            }
        }

        return new MappingApplyResult
        {
            RolesByElement = roles,
            ElementStreams = streams,
            Parameters = parameters,
            Measures = ParseMeasures(root, "measures"),
            Bindings = bindings,
        };
    }

    private static List<MappingMeasureState> ParseMeasures(JsonElement root, string key)
    {
        var list = new List<MappingMeasureState>();
        if (!root.TryGetProperty(key, out var ms) || ms.ValueKind != JsonValueKind.Array)
        {
            return list;
        }

        foreach (var m in ms.EnumerateArray())
        {
            string? iri = Text(m, "propertyIri");
            string? label = null;
            if (m.TryGetProperty("property", out var prop) && prop.ValueKind == JsonValueKind.Object)
            {
                iri = Text(prop, "iri");
                label = Text(prop, "label");
            }
            else if (iri is null && m.TryGetProperty("candidates", out var cands) && cands.ValueKind == JsonValueKind.Array && cands.GetArrayLength() > 0)
            {
                iri = Text(cands[0], "propertyIri");
                label = Text(cands[0], "label");
            }

            list.Add(new MappingMeasureState(Text(m, "nativeId") ?? string.Empty, Text(m, "name") ?? string.Empty, Text(m, "state") ?? "applied", label ?? LocalName(iri), iri, Text(m, "stream")));
        }

        return list;
    }

    private static List<MappingParameterState> ParseParameters(JsonElement root)
    {
        var list = new List<MappingParameterState>();
        if (!root.TryGetProperty("parameters", out var ps) || ps.ValueKind != JsonValueKind.Array)
        {
            return list;
        }

        foreach (var p in ps.EnumerateArray())
        {
            string? label = null;
            string? iri = null;
            if (p.TryGetProperty("property", out var prop) && prop.ValueKind == JsonValueKind.Object)
            {
                iri = Text(prop, "iri");
                label = Text(prop, "label") ?? LocalName(iri);
            }
            else if (p.TryGetProperty("candidates", out var cands) && cands.ValueKind == JsonValueKind.Array && cands.GetArrayLength() > 0)
            {
                var first = cands[0];
                iri = Text(first, "propertyIri");
                label = Text(first, "label") ?? LocalName(iri);
            }

            list.Add(new MappingParameterState(Text(p, "nativeId") ?? string.Empty, Text(p, "name") ?? string.Empty, Text(p, "state") ?? "unmapped", label, iri));
        }

        return list;
    }

    public static string? LocalName(string? iri)
    {
        if (string.IsNullOrEmpty(iri))
        {
            return iri;
        }

        var cut = iri.LastIndexOfAny(new[] { '#', '/', ':' });
        return cut >= 0 ? iri[(cut + 1)..] : iri;
    }

    private static string? Text(JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String
            ? v.GetString()
            : null;

    private static string ErrorCode(string text)
    {
        try
        {
            using var doc = JsonDocument.Parse(text);
            var root = doc.RootElement;
            if (root.TryGetProperty("detail", out var detail))
            {
                if (detail.ValueKind == JsonValueKind.Object && detail.TryGetProperty("code", out var code) && code.ValueKind == JsonValueKind.String)
                {
                    return code.GetString()!;
                }

                if (detail.ValueKind == JsonValueKind.String)
                {
                    return detail.GetString()!;
                }
            }

            if (root.TryGetProperty("code", out var c) && c.ValueKind == JsonValueKind.String)
            {
                return c.GetString()!;
            }
        }
        catch
        {
            // not JSON
        }

        return "HTTP_ERROR";
    }

    private static string Normalize(string url) => (string.IsNullOrWhiteSpace(url) ? "http://localhost:8000" : url.Trim()).TrimEnd('/');
}
