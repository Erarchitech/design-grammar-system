#if GRASSHOPPER_SDK
using System.Drawing;
using DG.Core.Parsing;

namespace DG.Grasshopper.Canvas;

/// <summary>
/// Shared color palette for the DG Canvas Annotation Convention (RESEARCH.md &#167;4) --
/// the write-path counterpart to <see cref="CanvasAnnotationNameFactory"/>. Maps every
/// <see cref="EntityTagKind"/> (plus the nested-Pattern variant) to the
/// <see cref="GH_Group"/> color <see cref="Components.EntityTagComponent"/> applies when it
/// wraps a canvas selection into a convention-named group.
///
/// [ASSUMED] Exact hex values are placeholders -- no Frame reference screenshot is checked
/// into the repo, only color names ("orange", "purple", "pink"). Confirm against the
/// architect's Frame reference before considering these locked (34-RESEARCH.md Assumptions
/// Log A5; flagged again in this plan's checkpoint:human-verify task).
/// </summary>
internal static class CanvasAnnotationStyles
{
    /// <summary>[ASSUMED] Procedure group color -- near-white/light gray.</summary>
    public static readonly Color Procedure = Color.FromArgb(255, 245, 245, 245);

    /// <summary>[ASSUMED] Pattern group color -- orange.</summary>
    public static readonly Color Pattern = Color.FromArgb(255, 243, 156, 18);

    /// <summary>[ASSUMED] Nested-Pattern group color -- purple.</summary>
    public static readonly Color NestedPattern = Color.FromArgb(255, 155, 89, 182);

    /// <summary>[ASSUMED] Parameter (Var/Const/Emg) group color -- pink.</summary>
    public static readonly Color Parameter = Color.FromArgb(255, 255, 182, 208);

    /// <summary>[ASSUMED] Interface group color -- near-white (distinct shade from Procedure).</summary>
    public static readonly Color Interface = Color.FromArgb(255, 250, 250, 250);

    /// <summary>
    /// Resolves the <see cref="Color"/> a new tag group should use for <paramref name="kind"/>.
    /// <paramref name="nested"/> selects the purple nested-Pattern variant instead of the
    /// standard orange Pattern color when the new group is being nested inside an existing
    /// Pattern group (CanvasContextExtractor.NestedGroupIds native-nesting contract).
    /// </summary>
    public static Color ForKind(EntityTagKind kind, bool nested) => kind switch
    {
        EntityTagKind.Proc => Procedure,
        EntityTagKind.Pat => nested ? NestedPattern : Pattern,
        EntityTagKind.Var => Parameter,
        EntityTagKind.Const => Parameter,
        EntityTagKind.Emg => Parameter,
        EntityTagKind.IntF => Interface,
        _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, "Unknown EntityTagKind."),
    };

    /// <summary>
    /// Phase 35 preview scaffold (CONTEXT decision #1): a desaturated, lower-alpha variant of
    /// a base group color for rendering an LLM-suggested (not-yet-tagged) entity preview. This
    /// phase only defines the constant; Phase 35 wires it into actual preview rendering.
    /// </summary>
    public static Color Preview(Color baseColor) =>
        Color.FromArgb(140, baseColor.R, baseColor.G, baseColor.B);

    /// <summary>
    /// Phase 35 preview name-prefix (RCGN-02): prepended to a pending LLM-suggested entity's
    /// display name so an unconfirmed proposal is visually distinct from a real tagged group
    /// name at a glance, alongside the desaturated <see cref="Preview(Color)"/> color.
    /// </summary>
    public const string PreviewPrefix = "[?] ";
}
#endif
