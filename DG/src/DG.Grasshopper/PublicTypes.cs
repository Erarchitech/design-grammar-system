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

public class ParamState : DG.Core.Models.ParamState
{
}

public class ObjState : DG.Core.Models.ObjState
{
}

public class PropState : DG.Core.Models.PropState
{
}

public class DesignState : DG.Core.Models.DesignState
{
}

public class DesignStateParameter : DG.Core.Models.DesignStateParameter
{
}

public class MetagraphHandle : DG.Core.Models.MetagraphHandle
{
}

public class OntologyClass : DG.Core.Models.OntologyClass
{
}

public class OntographHandle : DG.Core.Models.OntographHandle
{
}

public class ValidGraphHandle : DG.Core.Models.ValidGraphHandle
{
}

public class SpecGraphHandle : DG.Core.Models.SpecGraphHandle
{
}

// ReinstatementResult, ReinstatementParameterReport, and ResolvedTarget are sealed in Core.
// They are accessed directly via DG.Core.Models namespace — no wrapper aliases needed.
// The REINSTATE component outputs them as generic objects that downstream consumers
// can cast to their Core types.
