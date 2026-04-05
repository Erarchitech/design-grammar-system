# Testing

## Framework

| Stack | Framework | Runner |
|---|---|---|
| C# (.NET 9) | **xUnit 2.9.2** | `dotnet test` via Visual Studio Test SDK 17.12 |
| Coverage | **coverlet 6.0.2** | Integrated via `coverlet.collector` NuGet |
| Python / JS | None | No automated tests for `data-service` or `graph-viewer` |

## Test Project

- **Location:** `DG/tests/DG.Tests/DG.Tests.csproj`
- **Target framework:** `net9.0`
- **References:** `DG.Core` project (not `DG.Grasshopper` — Grasshopper components are not unit tested)

## Test Files

| Test File | Tests | What It Validates |
|---|---|---|
| `SwrlRuleParserTests.cs` | 1 test | SWRL string parsing: extracts body/head atoms and variables from expression |
| `RuleEvaluatorTests.cs` | 2+ tests | Rule evaluation: violation detection with bindings; variable name matching with/without `?` prefix |
| `VariableBinderTests.cs` | 2+ tests | Variable binding: zipping variables × values into `BindingRow`s; attaching `ElementRef`s to rows |
| `FailingBindingFormatterTests.cs` | — | Formatting failing bindings for display output |
| `ValidationPublishPackageBuilderTests.cs` | — | Building Speckle publish payloads from validation results |

## Test Patterns

### Arrange-Act-Assert
All tests follow the standard xUnit pattern:
```csharp
[Fact]
public void Parse_ShouldExtractAtomsAndVariables()
{
    // Arrange — build SWRL string
    const string swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)";
    // Act — parse
    var parsed = SwrlRuleParser.Parse(swrl);
    // Assert — verify structure
    Assert.Equal(3, parsed.BodyAtoms.Count);
}
```

### In-Memory Only
- All tests run against in-memory domain models — no Neo4j connection required
- `Rule`, `BindingRow`, `Variable` objects constructed inline
- No mocking framework used (xUnit only, no Moq/NSubstitute)

### Typical Test Values
- Building domain: `Building(?b)`, `hasHeightM(?b,?h)`, `swrlb:greaterThan(?h,75)`
- Binding values: decimal literals (`70m`, `80m`), string identifiers (`"B1"`, `"B2"`)
- Entity refs: `DgEntityId = "DG-1"`, `DisplayName = "Building 1"`

## Coverage Gaps

### Not Covered
- **`data-service/app.py`** — no Python tests at all (no pytest, no test directory)
- **`graph-viewer/index.html`** — no JS tests (no jest/vitest/playwright)
- **`graph-viewer/model-viewer/`** — no tests for the Speckle viewer React app
- **n8n workflows** — no automated validation of workflow JSON structure
- **Grasshopper components** — `DG.Grasshopper` is not referenced by test project (requires Rhino SDK)
- **Integration tests** — no end-to-end tests spanning multiple services
- **`Neo4jConnectorService`** and **`Neo4jRuleRepository`** — require live Neo4j, not tested

### Covered
- Core domain logic: SWRL parsing, rule evaluation, variable binding, formatting, publish package building
- All coverage is at the `DG.Core` library level

## CI / CD

- No CI pipeline configuration found (no `.github/workflows/`, no `Makefile`, no `Justfile`)
- Tests run manually via `dotnet test` or Visual Studio
- Docker builds do not execute tests as part of the build process

## Ad-Hoc Test Files

`test/` directory contains manual/exploratory test data:
- `test_cleanup.js`, `test_consolidation.js` — Node.js scripts for Neo4j data manipulation
- `training_dataset.json` — training data for LLM
- `records*.json`, `neo4j_res*.json` — captured Neo4j query results
- `CaseStudy_LivingUnit/` — case study test data
- `whisper_server.py` — speech-to-text server (likely experimental)
