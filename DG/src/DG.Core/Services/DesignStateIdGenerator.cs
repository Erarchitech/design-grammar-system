using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using DG.Core.Models;

namespace DG.Core.Services;

/// <summary>
/// Deterministic ID generation for the DG state model hierarchy.
///
/// <para>
/// <b>Two-layer DesignState identity (Phase 1202, D-01).</b> A DesignState carries two
/// independent identifiers, not one:
/// </para>
/// <list type="number">
/// <item>
/// <b>Layer 1 — the node key (capture-event identity):</b>
/// <see cref="ComputeCaptureEventStateId"/> folds the capture timestamp into the id, so two
/// captures of an otherwise-unchanged design are two distinct nodes. <b>Direct consequence:</b>
/// MERGE by StateId + project no longer dedupes a recapture — the graph grows per capture,
/// where the pre-1202 content-addressed scheme (below) treated a recapture as idempotent. This
/// changes the amended-Phase-38 MERGE contract (<c>spec/DATABASE.md</c>'s VALIDATOR-publish and
/// <c>POST /computgraph/candidates/accept</c> rows, mirrored by
/// <c>data-service/cg_paramstate_store.py</c>'s MERGE on <c>StateId</c> + <c>project</c>) for
/// any writer that switches to this overload — that re-examination is deliberate, not an
/// oversight, per D-01's own consequence note in 1202-CONTEXT.md.
/// </item>
/// <item>
/// <b>Layer 2 — the content hash:</b>
/// <see cref="DG.Core.Serialization.DesignStateCanonicalProjection.ComputeHash"/>, stored as the
/// <c>canonicalStateHash</c> property. This is queryable — two designs captured at different
/// times with identical content share a hash — but it is explicitly <b>not identity-bearing</b>:
/// it must never be used as (or substituted for) a node key, and it is not a Signature/MAC —
/// SHA-256 here is content-addressing, not an authenticity control.
/// </item>
/// </list>
/// <para>
/// <see cref="ComputeDesignStateId"/> (the pure content-addressed overload below) is retained
/// <b>unchanged</b> and is the function that minted every historical StateId before this phase.
/// Per D-03, historical states are treated additively with no rewrite: existing rows stay as-is
/// and are documented as pre-contract; only new captures adopt the capture-event key.
/// </para>
/// <para>
/// <see cref="ComputeParamStateId"/>, <see cref="ComputeObjectStateId"/>,
/// <see cref="ComputeObjectStateIdFromRef"/>, and <see cref="ComputePropStateId"/> are
/// member-level minting, cross-referenced here for completeness — they are unaffected by this
/// aggregate-level two-layer identity change; each remains a single content-addressed id for its
/// own state kind.
/// </para>
/// </summary>
public static class DesignStateIdGenerator
{
    private const string ParamStatePrefix = "DS_";
    private const string ObjectStatePrefix = "OS_";
    private const string PropStatePrefix = "PS_";
    private const string DesignStatePrefix = "DS_";

    /// <summary>
    /// IdRef = ParamState.StateId, reused (not separately hashed) — wired into DESIGN STATE
    /// component output in Phase 9 per CMPST-08.
    /// </summary>
    public const string IdRefPrefix = "IDR_";

    /// <summary>
    /// Produces a 16-character hex StateId, DS_-prefixed, deterministic over the sorted
    /// parameter ID + value pairs. Identical parameter sets always produce the same StateId.
    /// </summary>
    public static string ComputeParamStateId(IEnumerable<DesignStateParameter> parameters)
    {
        var sb = new StringBuilder();

        foreach (var p in parameters.OrderBy(x => x.ParameterId, StringComparer.Ordinal))
        {
            sb.Append(p.ParameterId);
            sb.Append('=');
            sb.Append(p.Type switch
            {
                DesignStateParameterType.Boolean => p.BooleanValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
                DesignStateParameterType.Integer => p.IntegerValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
                DesignStateParameterType.Number => p.NumberValue?.ToString("R", CultureInfo.InvariantCulture) ?? "null",
                _ => "null",
            });
            sb.Append(';');
        }

        return ParamStatePrefix + HashToHex16(sb.ToString());
    }

    /// <summary>
    /// Produces an OS_-prefixed StateId: OS_&lt;SHA256(projectId + objectInstanceId + variableName)&gt;
    /// for the ObjState model. Cross-rule (no rule-scoping input) per CMPST-07 — Object variables
    /// are shared across rules.
    /// </summary>
    public static string ComputeObjectStateId(string projectId, string objectInstanceId, string variableName)
    {
        var input = $"{projectId}|{objectInstanceId}|{variableName}";
        return ObjectStatePrefix + HashToHex16(input);
    }

    /// <summary>
    /// Produces an OS_-prefixed StateId: OS_&lt;SHA256(objectRef|classIri-or-sentinel)&gt; for the
    /// ObjState model, from what the OBJECT STATE Grasshopper component actually has on its
    /// canvas (an <c>objectRef</c> and a resolved <c>classIri</c>) rather than the per-rule-variable
    /// inputs <see cref="ComputeObjectStateId"/> expects.
    ///
    /// <para>
    /// <b>Why this exists alongside <see cref="ComputeObjectStateId"/>:</b> the 3-arg method above
    /// is the per-rule-variable form (CMPST-07 — Object variables shared across rules, keyed by
    /// project + instance + variable name); its semantics are deliberately different and it is
    /// left untouched. <c>ObjectStateComponent</c> has no Project input port and no
    /// per-geometry-instance variable-name concept, so synthesizing fake values for either would
    /// satisfy the signature in name while destroying the meaning the 3-arg method's own
    /// doc-comment promises. This overload is the per-geometry-instance form the component
    /// actually needs (Phase 1202, D-04).
    /// </para>
    /// <para>
    /// <b>Label is deliberately NOT folded in</b> — this reverses the behavior of the private
    /// duplicate this overload replaces (<c>ObjectStateComponent.ComputeObjStateId</c>, deleted),
    /// which hashed <c>objectRef|label</c>. Renaming an object's Label no longer changes its
    /// ObjState identity; only its <c>objectRef</c> and <c>classIri</c> do, because those are what
    /// the object structurally *is*, not how it is currently displayed.
    /// </para>
    /// <para>
    /// A null <paramref name="classIri"/> (captured before a class is wired) is hashed against a
    /// stable sentinel rather than an empty string or a crash, so the id is still deterministic.
    /// </para>
    /// </summary>
    public static string ComputeObjectStateIdFromRef(string objectRef, string? classIri)
    {
        const string NoClassIriSentinel = "\u0000no-class-iri\u0000";
        var input = $"{objectRef}|{classIri ?? NoClassIriSentinel}";
        return ObjectStatePrefix + HashToHex16(input);
    }

    /// <summary>
    /// Produces a PS_-prefixed StateId for PropState: PS_&lt;SHA256(ruleIri|dataPropertyIri|propValueLex[|objectRef])&gt;.
    /// Deterministic over the Rule IRI, DataProperty IRI, and the typed property value.
    /// When <paramref name="objectRef"/> is provided (per-object properties), it is folded into
    /// the hash so two objects sharing the same value get distinct StateIds (no MERGE collision).
    /// Same Rule + DataProperty + value (+ object) → same StateId across validation runs.
    /// </summary>
    public static string ComputePropStateId(
        string ruleIri,
        string dataPropertyIri,
        DesignStateParameter propValue,
        string? objectRef = null)
    {
        var lex = propValue.Type switch
        {
            DesignStateParameterType.Number => propValue.NumberValue?.ToString("R", CultureInfo.InvariantCulture) ?? "null",
            DesignStateParameterType.Integer => propValue.IntegerValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
            DesignStateParameterType.Boolean => propValue.BooleanValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
            _ => "null",
        };

        var input = string.IsNullOrWhiteSpace(objectRef)
            ? $"{ruleIri}|{dataPropertyIri}|{lex}"
            : $"{ruleIri}|{dataPropertyIri}|{lex}|{objectRef}";
        return PropStatePrefix + HashToHex16(input);
    }

    /// <summary>
    /// Produces a DS_-prefixed aggregate StateId for DesignState: DS_&lt;SHA256(sorted member StateIds)&gt;.
    /// Deterministic over sorted member StateIds. Same member set → same StateId → dedup across
    /// validation runs via MERGE by StateId+project. The DS_ prefix is shared with ParamStatePrefix
    /// but the hash input domains differ (parameters vs. member StateId concatenation), so IDs from
    /// the two methods are distinct.
    /// </summary>
    public static string ComputeDesignStateId(IEnumerable<string> memberStateIds)
    {
        var sb = new StringBuilder();
        foreach (var id in memberStateIds.OrderBy(x => x, StringComparer.Ordinal))
        {
            sb.Append(id);
        }

        return DesignStatePrefix + HashToHex16(sb.ToString());
    }

    /// <summary>
    /// Produces a DS_-prefixed capture-event StateId — the D-01 layer 1 node key. Additive
    /// alongside <see cref="ComputeDesignStateId"/>, which remains byte-identical and is the
    /// function that minted every historical StateId (D-03).
    ///
    /// Hash input: the ordinally-sorted member StateIds concatenated exactly as
    /// <see cref="ComputeDesignStateId"/> already does, followed by a <c>|</c> separator and the
    /// ISO-8601 round-trip ("O", invariant culture, UTC) rendering of
    /// <paramref name="capturedAtUtc"/> — the same rendering
    /// <see cref="DG.Core.Serialization.DesignStatePayloadV2Serializer"/> already uses, so this
    /// id and the payload's own <c>capturedAtUtc</c> field never disagree.
    ///
    /// Deterministic and idempotent: the same members captured at the same instant always
    /// produce the same id (so a retried write of the same capture is still idempotent), but two
    /// captures of the same members at two different instants produce two distinct ids — the
    /// direct consequence documented on this class's own doc-comment (MERGE by StateId + project
    /// no longer dedupes a recapture).
    /// </summary>
    public static string ComputeCaptureEventStateId(IEnumerable<string> memberStateIds, DateTimeOffset capturedAtUtc)
    {
        var sb = new StringBuilder();
        foreach (var id in memberStateIds.OrderBy(x => x, StringComparer.Ordinal))
        {
            sb.Append(id);
        }

        sb.Append('|');
        sb.Append(capturedAtUtc.UtcDateTime.ToString("O", CultureInfo.InvariantCulture));

        return DesignStatePrefix + HashToHex16(sb.ToString());
    }

    private static string HashToHex16(string input)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(hash)[..16];
    }
}
