using System.Text.Json;
using DG.Core.Validation;

namespace DG.Tests;

/// <summary>
/// Round-trip deserialization test for the SHACL DTOs consumed by
/// ValidationPublishResponse.Shacl (DG.Grasshopper.Validation.ValidationPublishContract).
///
/// DG.Tests targets net9.0 and cannot ProjectReference DG.Grasshopper (net7.0-windows7.0 —
/// NU1201 TFM incompatibility confirmed during Plan 823-05 execution), and the DTOs there are
/// `internal sealed` with no InternalsVisibleTo for DG.Tests. Per the plan's own camelCase
/// round-trip requirement (RESEARCH Pitfall 4), the payload DTOs are defined as public types in
/// DG.Core.Validation instead, and ValidationPublishResponse.Shacl (DG.Grasshopper) references
/// them directly. This test exercises the exact same types the response wraps.
/// </summary>
public sealed class ValidationPublishResponseShaclTests
{
    private const string ShaclJson = """
        {
          "status": "ok",
          "conforms": true,
          "counts": { "violation": 1, "warning": 1, "info": 1 },
          "results": [
            {
              "severity": "violation",
              "what": "Door width below minimum",
              "where": "focus:Door_12",
              "howToFix": "Increase width to at least 900mm",
              "focusLabel": "Door 12",
              "shapeId": "shape:DoorWidthShape"
            },
            {
              "severity": "warning",
              "what": "Room area unusually small",
              "where": "focus:Room_04",
              "howToFix": "Verify the room area is intentional",
              "focusLabel": "Room 04",
              "shapeId": "shape:RoomAreaShape"
            },
            {
              "severity": "info",
              "what": "Wall thickness not specified",
              "where": "focus:Wall_09",
              "howToFix": "Consider adding an explicit thickness value",
              "focusLabel": "Wall 09",
              "shapeId": "shape:WallThicknessShape"
            }
          ]
        }
        """;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    [Fact]
    public void Deserialize_PopulatedShaclBlock_YieldsAllFieldsNonEmpty()
    {
        var report = JsonSerializer.Deserialize<ShaclReportPayload>(ShaclJson, JsonOptions);

        Assert.NotNull(report);
        Assert.Equal("ok", report!.Status);
        Assert.True(report.Conforms);
        Assert.NotNull(report.Counts);
        Assert.Equal(1, report.Counts!.Violation);
        Assert.Equal(1, report.Counts.Warning);
        Assert.Equal(1, report.Counts.Info);
        Assert.Equal(3, report.Results.Count);

        foreach (var finding in report.Results)
        {
            Assert.False(string.IsNullOrEmpty(finding.Severity));
            Assert.False(string.IsNullOrEmpty(finding.What));
            Assert.False(string.IsNullOrEmpty(finding.Where));
            Assert.False(string.IsNullOrEmpty(finding.HowToFix));
            Assert.False(string.IsNullOrEmpty(finding.FocusLabel));
            Assert.False(string.IsNullOrEmpty(finding.ShapeId));
        }
    }

    [Fact]
    public void Deserialize_ViolationFinding_MapsEveryCamelCaseFieldExactly()
    {
        var report = JsonSerializer.Deserialize<ShaclReportPayload>(ShaclJson, JsonOptions);
        var violation = report!.Results[0];

        Assert.Equal("violation", violation.Severity);
        Assert.Equal("Door width below minimum", violation.What);
        Assert.Equal("focus:Door_12", violation.Where);
        Assert.Equal("Increase width to at least 900mm", violation.HowToFix);
        Assert.Equal("Door 12", violation.FocusLabel);
        Assert.Equal("shape:DoorWidthShape", violation.ShapeId);
    }
}
