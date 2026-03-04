#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Parsing;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using System.Drawing;
using CoreVariable = DG.Core.Models.Variable;

namespace DG.Grasshopper.Components;

public sealed class RuleDeconstructComponent : GH_Component
{
    private static readonly string[] ExpectedOutputNames =
    {
        "Rule",
        "Variables",
        "VariableName",
        "SWRL",
        "RuleName",
        "RuleDescription",
    };

    public RuleDeconstructComponent()
        : base("RULE DECONSTRUCT", "RULE DECONSTRUCT", "Extract variables, SWRL, and metadata from DG.Rule.", DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("1D5AD920-C5DB-4C07-BF66-BA4E2526E6D4");

    protected override Bitmap Icon => DgIcons.RuleDeconstruct24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Rule", "Rule", "DG.Rule input", GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Rule", "Rule", "Rule pass-through", GH_ParamAccess.item);
        pManager.AddGenericParameter("Variables", "Variables", "Unique DG.Variable list", GH_ParamAccess.list);
        pManager.AddTextParameter("VariableName", "VariableName", "Variable names without '?' prefix", GH_ParamAccess.list);
        pManager.AddTextParameter("SWRL", "SWRL", "SWRL expression", GH_ParamAccess.item);
        pManager.AddTextParameter("RuleName", "RuleName", "Rule name", GH_ParamAccess.item);
        pManager.AddTextParameter("RuleDescription", "RuleDescription", "Rule description", GH_ParamAccess.item);
    }

    public override void AddedToDocument(GH_Document document)
    {
        base.AddedToDocument(document);
        EnsureOutputLayout();
    }

    public override bool Read(GH_IO.Serialization.GH_IReader reader)
    {
        var ok = base.Read(reader);
        EnsureOutputLayout();
        return ok;
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? ruleInput = null;
        if (!da.GetData(0, ref ruleInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Rule input is required.");
            return;
        }

        var rule = GhCastingHelpers.TryRule(ruleInput);
        if (rule is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast Rule input.");
            return;
        }

        var variablesByName = new Dictionary<string, CoreVariable>(StringComparer.Ordinal);
        foreach (var variable in rule.Variables)
        {
            if (string.IsNullOrWhiteSpace(variable.Name))
            {
                continue;
            }

            variablesByName[variable.Name] = variable;
        }

        if (!string.IsNullOrWhiteSpace(rule.Swrl))
        {
            var parsed = SwrlRuleParser.Parse(rule.Swrl);
            foreach (var variable in parsed.Variables)
            {
                if (!variablesByName.ContainsKey(variable.Name))
                {
                    variablesByName[variable.Name] = new CoreVariable
                    {
                        Name = variable.Name,
                        InferredDatatype = variable.InferredDatatype,
                    };
                }
            }
        }

        var variables = variablesByName.Values
            .OrderBy(variable => variable.Name, StringComparer.Ordinal)
            .ToList();

        var publicVars = variables
            .Select(variable => new global::DG.Variable
            {
                Name = variable.Name,
                InferredDatatype = variable.InferredDatatype,
            })
            .ToList();
        var variableNames = publicVars
            .Select(variable => (variable.Name ?? string.Empty).Trim())
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Select(name => name.StartsWith("?", StringComparison.Ordinal) ? name[1..] : name)
            .Distinct(StringComparer.Ordinal)
            .ToList();

        var publicRule = new global::DG.Rule
        {
            Id = rule.Id,
            Name = rule.Name,
            Description = rule.Description,
            Kind = rule.Kind,
            Text = rule.Text,
            Swrl = rule.Swrl,
            Project = rule.Project,
            Graph = rule.Graph,
        };
        foreach (var atom in rule.BodyAtoms)
        {
            publicRule.BodyAtoms.Add(atom);
        }

        foreach (var atom in rule.HeadAtoms)
        {
            publicRule.HeadAtoms.Add(atom);
        }

        foreach (var variable in rule.Variables)
        {
            publicRule.Variables.Add(new global::DG.Variable
            {
                Name = variable.Name,
                InferredDatatype = variable.InferredDatatype,
            });
        }

        da.SetData(0, publicRule);
        da.SetDataList(1, publicVars);
        da.SetDataList(2, variableNames);
        da.SetData(3, rule.Swrl);
        da.SetData(4, rule.Name);
        da.SetData(5, rule.Description);
        Message = $"{publicVars.Count} vars";
    }

    private void EnsureOutputLayout()
    {
        if (HasExpectedOutputLayout())
        {
            return;
        }

        var outputs = Params.Output.ToList();
        for (var index = outputs.Count - 1; index >= 0; index--)
        {
            Params.UnregisterOutputParameter(outputs[index], true);
        }

        Params.RegisterOutputParam(new Param_GenericObject
        {
            Name = "Rule",
            NickName = "Rule",
            Description = "Rule pass-through",
            Access = GH_ParamAccess.item,
        });
        Params.RegisterOutputParam(new Param_GenericObject
        {
            Name = "Variables",
            NickName = "Variables",
            Description = "Unique DG.Variable list",
            Access = GH_ParamAccess.list,
        });
        Params.RegisterOutputParam(new Param_String
        {
            Name = "VariableName",
            NickName = "VariableName",
            Description = "Variable names without '?' prefix",
            Access = GH_ParamAccess.list,
        });
        Params.RegisterOutputParam(new Param_String
        {
            Name = "SWRL",
            NickName = "SWRL",
            Description = "SWRL expression",
            Access = GH_ParamAccess.item,
        });
        Params.RegisterOutputParam(new Param_String
        {
            Name = "RuleName",
            NickName = "RuleName",
            Description = "Rule name",
            Access = GH_ParamAccess.item,
        });
        Params.RegisterOutputParam(new Param_String
        {
            Name = "RuleDescription",
            NickName = "RuleDescription",
            Description = "Rule description",
            Access = GH_ParamAccess.item,
        });

        Params.OnParametersChanged();
        ExpireSolution(recompute: true);
    }

    private bool HasExpectedOutputLayout()
    {
        if (Params.Output.Count != ExpectedOutputNames.Length)
        {
            return false;
        }

        for (var index = 0; index < ExpectedOutputNames.Length; index++)
        {
            var output = Params.Output[index];
            if (!string.Equals(output.Name, ExpectedOutputNames[index], StringComparison.Ordinal))
            {
                return false;
            }
        }

        return true;
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class RuleDeconstructComponent
{
}
#endif
