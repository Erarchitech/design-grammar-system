namespace DG.Core.Parsing;

/// <summary>
/// Shared grammar-token constants for the DG Canvas Annotation Convention
/// (RESEARCH.md &#167;4). Mirrors the literal tokens embedded in
/// <see cref="CanvasAnnotationParser"/>'s regexes so the write path
/// (<see cref="CanvasAnnotationNameFactory"/>) can build names the parser
/// reads back symmetrically. <see cref="CanvasAnnotationParser"/> itself is
/// never edited to reference these constants -- its locked source-inspection
/// test (<c>CanvasAnnotationParserSource_UsesCompiledAnchoredGrammarRegexes</c>)
/// asserts the literal regex strings appear verbatim in its source. Drift
/// between the parser's literals and these constants is instead caught by
/// <c>Grammar_ConstantsAppearVerbatimInParserSource</c> in
/// <c>CanvasAnnotationNameFactoryTests.cs</c>.
/// </summary>
public static class CanvasAnnotationGrammar
{
    public const string ObjectPrefix = "OBJECT - ";

    public const string AlgorithmSuffix = "_ALGORITHM";

    public const string ProcedureInfix = "_Proc - ";

    public const string PatternInfix = "_Pat_";

    public const string VariableInfix = "_Var_";

    public const string ConstantInfix = "_Const_";

    /// <summary>Canonical Emergent infix -- always emitted by the write path.</summary>
    public const string EmergentInfix = "_Emg_";

    /// <summary>
    /// Tolerated typo variant of <see cref="EmergentInfix"/> -- the parser normalizes it
    /// to Emergent with a warning, but the write path NEVER emits it.
    /// </summary>
    public const string EmergentToleratedInfix = "_Emr_";

    public const string InterfaceInfix = "_IntF_";

    /// <summary>
    /// All infix tokens that would make a user-supplied <c>Name</c> re-parse as a
    /// different grammar Kind if left unvalidated (T-34-01). Used by
    /// <see cref="CanvasAnnotationNameFactory"/>'s name validation.
    /// </summary>
    public static readonly string[] ReservedInfixTokens =
    {
        ProcedureInfix,
        PatternInfix,
        VariableInfix,
        ConstantInfix,
        EmergentInfix,
        EmergentToleratedInfix,
        InterfaceInfix,
    };
}
