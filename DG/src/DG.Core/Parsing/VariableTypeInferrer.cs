using DG.Core.Models;

namespace DG.Core.Parsing;

public static class VariableTypeInferrer
{
    public static VariableKind? Infer(Rule rule, string variableName)
    {
        var atoms = rule.BodyAtoms.Concat(rule.HeadAtoms);

        var seenInAnyAtom = false;

        foreach (var atom in atoms)
        {
            foreach (var arg in atom.Args)
            {
                if (arg.Kind != ArgKind.Variable || !string.Equals(arg.Value, variableName, StringComparison.Ordinal))
                {
                    continue;
                }

                seenInAnyAtom = true;

                if (atom.Type == "ClassAtom" && arg.Pos == 1)
                {
                    // Priority 1: Object wins as soon as the variable is the subject of any ClassAtom,
                    // even if it also appears in a DataPropertyAtom elsewhere in the rule.
                    return VariableKind.Object;
                }
            }
        }

        foreach (var atom in atoms)
        {
            if (atom.Type != "DataPropertyAtom")
            {
                continue;
            }

            foreach (var arg in atom.Args)
            {
                if (arg.Kind == ArgKind.Variable
                    && string.Equals(arg.Value, variableName, StringComparison.Ordinal)
                    && arg.Pos >= 2)
                {
                    // Priority 2: Property when only ever seen at pos-2+ of a DataPropertyAtom
                    // (no ClassAtom subject match found above).
                    return VariableKind.Property;
                }
            }
        }

        if (!seenInAnyAtom)
        {
            // Priority 5: variable not present in the rule at all.
            return null;
        }

        // Priority 3/4: variable appears only inside BuiltinAtom args (or only at non-qualifying
        // positions, e.g. pos-1 of a DataPropertyAtom without a corresponding ClassAtom match) —
        // not exposed to canvas as Object or Property. Indeterminate.
        return null;
    }
}
