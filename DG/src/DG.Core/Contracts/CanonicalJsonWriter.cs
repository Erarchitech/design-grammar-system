using System;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;

namespace DG.Core.Contracts;

/// <summary>
/// Canonical-JSON serialization and hashing (spec/EVIDENCE-CONTRACT.md section 6, D-07).
///
/// Cross-language parity contract: this class is byte-identical in behavior to
/// <c>data-service/canonical_json.py</c> (the Python mirror, plan 1200-03). Any change to the
/// normalization rules here breaks cross-platform evidence-hash parity between C# (<c>DG.Core</c>)
/// and Python (data-service, dg-reasoner). The shared golden vectors in
/// <c>fixtures/golden/canonical-vectors.json</c>, asserted by <c>CanonicalJsonWriterTests</c>, are
/// what guard this parity — a divergence fails a test in whichever leg drifted, before any
/// DE-01 cross-leg comparison could report it as a disagreement.
///
/// Two hashing conventions:
/// 1. <see cref="HashScalarTuple"/> — for a fixed, ordered list of scalar strings (e.g. minting a
///    dgId). This is the shipped precedent already in production:
///    <see cref="DG.Core.Models.Identity.DgIdMintingService.Mint"/> pipe-joins its parts, SHA-256s
///    the UTF-8 bytes, and renders the digest as uppercase hex. No canonical-JSON step is needed
///    for this class of hash — the ordered pipe-join already is the canonical form.
/// 2. <see cref="Canonicalize"/> / <see cref="HashCanonical"/> — for a hash input that is a nested
///    JSON payload (arrays, objects), implementing the six normalization rules from
///    spec/EVIDENCE-CONTRACT.md section 6 by an explicit recursive walk, never by delegating to
///    <see cref="System.Text.Json.JsonSerializer"/> — <c>System.Text.Json</c> preserves declaration
///    order and applies broader default escaping by default, so its defaults cannot produce the
///    canonical form (1200-RESEARCH.md Pitfall 2).
///
/// Changing any of the six canonicalization rules requires bumping
/// <see cref="CanonicalizationVersion"/>, because a recorded hash in already-committed evidence
/// becomes meaningless if the rules that produced it change silently underneath it.
/// </summary>
public static class CanonicalJsonWriter
{
    public const int CanonicalizationVersion = 1;

    /// <summary>
    /// Pipe-joins <paramref name="parts"/>, SHA-256s the UTF-8 bytes, and returns the full 64-char
    /// uppercase hex digest. Mirrors <see cref="DG.Core.Models.Identity.DgIdMintingService.Mint"/>
    /// and <c>data-service/canonical_json.py</c>'s <c>hash_scalar_tuple</c> byte-for-byte. Callers
    /// wanting the 16-char dgId-style truncation do that themselves.
    /// </summary>
    public static string HashScalarTuple(params string[] parts)
    {
        if (parts is null || parts.Length == 0)
        {
            throw new ArgumentException("HashScalarTuple requires at least one part.", nameof(parts));
        }

        for (var i = 0; i < parts.Length; i++)
        {
            if (string.IsNullOrWhiteSpace(parts[i]))
            {
                throw new ArgumentException($"HashScalarTuple part at position {i} must not be null, empty, or whitespace-only.", nameof(parts));
            }
        }

        var joined = string.Join("|", parts);
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(joined));
        return Convert.ToHexString(hash);
    }

    /// <summary>
    /// Produces the canonical serialization of <paramref name="node"/>, implementing all six
    /// D-07 rules:
    /// 1. Object keys sorted ascending by Unicode code point (ordinal), not culture-aware.
    /// 2. Integers rendered with no decimal point/leading zeros; non-integers only from
    ///    <see cref="decimal"/> as fixed-point strings; <see cref="double"/>/<see cref="float"/>
    ///    throw, because IEEE-754 "shortest round-trip" formatting diverges between .NET and
    ///    Python.
    /// 3. No insignificant whitespace — bare <c>,</c> and <c>:</c> separators.
    /// 4. Every string value and object key normalized to Unicode NFC.
    /// 5. Only <c>"</c>, <c>\</c>, and control characters below <c>0x20</c> are escaped;
    ///    non-ASCII is left unescaped. This deliberately differs from
    ///    <see cref="System.Text.Json.JsonSerializer"/>'s default broader escaping — the Python
    ///    equivalent is <c>ensure_ascii=False</c> — and is acceptable because this canonical form
    ///    is hashed and never rendered into HTML.
    /// 6. NaN and Infinity throw — never representable in canonical form. A producer whose
    ///    computation would otherwise emit one should instead report the <c>indeterminate</c> or
    ///    <c>error</c> canonical status for that result.
    ///
    /// Implemented as an explicit recursive walk over <see cref="JsonNode"/>, never delegating to
    /// the standard library's generic serializer method.
    /// </summary>
    public static string Canonicalize(JsonNode? node)
    {
        var sb = new StringBuilder();
        WriteNode(node, sb, "<root>");
        return sb.ToString();
    }

    /// <summary>Canonicalizes <paramref name="node"/>, SHA-256s the UTF-8 bytes, returns uppercase hex.</summary>
    public static string HashCanonical(JsonNode? node)
    {
        var canonical = Canonicalize(node);
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(canonical));
        return Convert.ToHexString(hash);
    }

    private static void WriteNode(JsonNode? node, StringBuilder sb, string path)
    {
        if (node is null)
        {
            sb.Append("null");
            return;
        }

        switch (node)
        {
            case JsonObject obj:
                WriteObject(obj, sb, path);
                return;
            case JsonArray arr:
                WriteArray(arr, sb, path);
                return;
            case JsonValue val:
                WriteValue(val, sb, path);
                return;
            default:
                throw new NotSupportedException($"CanonicalJsonWriter: field '{path}' has unsupported JsonNode type {node.GetType().Name}.");
        }
    }

    private static void WriteObject(JsonObject obj, StringBuilder sb, string path)
    {
        // Rule 1: keys sorted ascending by Unicode code point (ordinal) — mirrors Python's
        // json.dumps(obj, sort_keys=True) for str keys. Keys are also NFC-normalized before
        // sorting/emitting (rule 4 applies to "every string value and every object key").
        var normalizedPairs = obj
            .Select(kvp => (Key: kvp.Key.Normalize(NormalizationForm.FormC), Value: kvp.Value))
            .OrderBy(p => p.Key, StringComparer.Ordinal)
            .ToArray();

        sb.Append('{');
        for (var i = 0; i < normalizedPairs.Length; i++)
        {
            if (i > 0)
            {
                sb.Append(',');
            }

            WriteString(normalizedPairs[i].Key, sb);
            sb.Append(':');
            WriteNode(normalizedPairs[i].Value, sb, $"{path}.{normalizedPairs[i].Key}");
        }

        sb.Append('}');
    }

    private static void WriteArray(JsonArray arr, StringBuilder sb, string path)
    {
        // Rule: arrays are ordered data — element order is preserved, only object keys are sorted.
        sb.Append('[');
        for (var i = 0; i < arr.Count; i++)
        {
            if (i > 0)
            {
                sb.Append(',');
            }

            WriteNode(arr[i], sb, $"{path}[{i}]");
        }

        sb.Append(']');
    }

    private static void WriteValue(JsonValue val, StringBuilder sb, string path)
    {
        if (val.TryGetValue<bool>(out var boolValue))
        {
            sb.Append(boolValue ? "true" : "false");
            return;
        }

        if (val.TryGetValue<string>(out var stringValue))
        {
            WriteString(stringValue.Normalize(NormalizationForm.FormC), sb);
            return;
        }

        if (val.TryGetValue<decimal>(out var decimalValue))
        {
            WriteNumberDecimal(decimalValue, sb, path);
            return;
        }

        if (val.TryGetValue<double>(out _) || val.TryGetValue<float>(out _))
        {
            throw new NotSupportedException($"CanonicalJsonWriter: field '{path}' is a double/float; IEEE-754 formatting diverges across languages. Use decimal for non-integer numbers, or represent a non-finite/indeterminate result via the 'indeterminate'/'error' canonical status instead.");
        }

        if (val.TryGetValue<long>(out var longValue))
        {
            sb.Append(longValue.ToString(CultureInfo.InvariantCulture));
            return;
        }

        if (val.TryGetValue<int>(out var intValue))
        {
            sb.Append(intValue.ToString(CultureInfo.InvariantCulture));
            return;
        }

        throw new NotSupportedException($"CanonicalJsonWriter: field '{path}' has an unsupported JsonValue kind ({val.GetType().Name}).");
    }

    private static void WriteNumberDecimal(decimal value, StringBuilder sb, string path)
    {
        // The decimal's stored scale is preserved deliberately, mirroring Python's
        // format(Decimal, "f") — trailing zeros are part of the value's canonical form, not
        // noise to be trimmed. Scale is read directly from the decimal's own bit representation
        // (bits 16-23 of the fourth int returned by decimal.GetBits) rather than inferred from
        // integrality, so 100.00m stays "100.00" and 2.50m stays "2.50".
        var bits = decimal.GetBits(value);
        var scale = (bits[3] >> 16) & 0xFF;

        if (scale == 0)
        {
            // Scale-0 decimal: no decimal point, matching format(Decimal("3"), "f") == "3".
            sb.Append(value.ToString(CultureInfo.InvariantCulture));
            return;
        }

        // Fixed-point string with exactly `scale` fractional digits, never scientific notation.
        sb.Append(value.ToString("F" + scale.ToString(CultureInfo.InvariantCulture), CultureInfo.InvariantCulture));
    }

    private static void WriteString(string s, StringBuilder sb)
    {
        sb.Append('"');
        foreach (var ch in s)
        {
            switch (ch)
            {
                case '"':
                    sb.Append("\\\"");
                    break;
                case '\\':
                    sb.Append("\\\\");
                    break;
                case '\b':
                    sb.Append("\\b");
                    break;
                case '\f':
                    sb.Append("\\f");
                    break;
                case '\n':
                    sb.Append("\\n");
                    break;
                case '\r':
                    sb.Append("\\r");
                    break;
                case '\t':
                    sb.Append("\\t");
                    break;
                default:
                    if (ch < 0x20)
                    {
                        sb.Append("\\u").Append(((int)ch).ToString("x4", CultureInfo.InvariantCulture));
                    }
                    else
                    {
                        // Non-ASCII characters are left unescaped (rule 5) — deliberate choice,
                        // this internal evidence JSON is never rendered into HTML.
                        sb.Append(ch);
                    }

                    break;
            }
        }

        sb.Append('"');
    }
}
