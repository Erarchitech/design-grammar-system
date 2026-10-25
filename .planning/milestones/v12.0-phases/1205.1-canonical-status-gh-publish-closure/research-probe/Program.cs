using System.Reflection;
using System.Net.Http.Json;
using System.Text.Json;
using DG.Core.Models;
using DG.Core.Validation;
using DG.Grasshopper.Validation;

var rule = new Rule { Id = "R_AUDIT", Project = "P_AUDIT" };
rule.BodyAtoms.Add(new Atom { Type = "ObjectPropertyAtom", PredicateLabel = "belongsTo" });
var binding = new BindingRow();
binding.ElementRefsByVar["b"] = new ElementRef { DgEntityId = "OBJ_AUDIT" };
var result = new RuleEvaluator().EvaluateRule(rule, new[] { binding });
var package = ValidationPublishPackageBuilder.Build(new[] { rule }, new[] { result }, new[] { binding });
var type = typeof(ValidationPublishClient);
var request = type.GetMethod("BuildRequest", BindingFlags.NonPublic | BindingFlags.Static)!.Invoke(null, new object?[] { package, null });
var options = (JsonSerializerOptions)type.GetField("JsonOptions", BindingFlags.NonPublic | BindingFlags.Static)!.GetValue(null)!;
using var content = JsonContent.Create((ValidationPublishRequest)request!, options: options);
Console.WriteLine(await content.ReadAsStringAsync());

namespace DG.Grasshopper.Validation
{
    // Only Rhino geometry is replaced. Production DTO, mapper and JSON options are linked unchanged.
    internal static class ValidationGeometryPayloadSerializer
    {
        public static ValidationGeometryPayload? Serialize(object? geometry) => geometry is null
            ? null : throw new InvalidOperationException("Research probe supports null geometry only.");
    }
}
