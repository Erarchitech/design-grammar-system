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
            if (atom.Type != "ObjectPropertyAtom")
            {
                continue;
            }

            foreach (var arg in atom.Args)
            {
                if (arg.Kind == ArgKind.Variable && string.Equals(arg.Value, variableName, StringComparison.Ordinal))
                {
                    // Priority 2: ObjectPropertyAtom relates two individuals, so either argument
                    // position (subject or object of the relation) is itself an Object — no
                    // ClassAtom subject match was found above for this variable.
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
                    && arg.Pos == 2)
                {
                    // Priority 3: Property when seen at pos-2 (the value position) of a
                    // DataPropertyAtom (no ClassAtom subject or ObjectPropertyAtom match found
                    // above). A well-formed DataPropertyAtom always has exactly 2 args — subject
                    // at pos-1, value at pos-2 (see cypher_template.txt) — so this is pinned to
                    // pos-2 exactly rather than ">= 2" to avoid silently accepting malformed/
                    // legacy data with unexpected extra args as Property.
                    return VariableKind.Property;
                }
            }
        }

        if (!seenInAnyAtom)
        {
            // Priority 5: variable not present in the rule at all.
            return null;
        }

        // Priority 4: variable appears only inside BuiltinAtom args (or only at non-qualifying
        // positions, e.g. pos-1 of a DataPropertyAtom without a corresponding ClassAtom or
        // ObjectPropertyAtom match) — not exposed to canvas as Object or Property. Indeterminate.
        return null;
    }
}
