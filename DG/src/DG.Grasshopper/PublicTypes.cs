namespace DG;

public class Rule : DG.Core.Models.Rule
{
}

public class Variable : DG.Core.Models.Variable
{
}

public class ElementRef : DG.Core.Models.ElementRef
{
}

public class DesignStateSnapshot : DG.Core.Models.DesignStateSnapshot
{
}

public class DesignStateParameter : DG.Core.Models.DesignStateParameter
{
}

// ReinstatementResult, ReinstatementParameterReport, and ResolvedTarget are sealed in Core.
// They are accessed directly via DG.Core.Models namespace — no wrapper aliases needed.
// The REINSTATE component outputs them as generic objects that downstream consumers
// can cast to their Core types.
