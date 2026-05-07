import { describe, it, expect } from "vitest";
import { useValidationRunsGrouping } from "./useValidationRunsGrouping.js";

const mkRun = (overrides) => ({
  runId: "r1",
  ruleIds: [],
  state: null,
  createdAt: "2026-05-01T10:00:00Z",
  ...overrides,
});

describe("useValidationRunsGrouping", () => {
  it("returns [] for empty input", () => {
    expect(useValidationRunsGrouping([], "rule")).toEqual([]);
    expect(useValidationRunsGrouping(null, "rule")).toEqual([]);
    expect(useValidationRunsGrouping(undefined, "state")).toEqual([]);
  });

  it("groups by first ruleId in rule mode", () => {
    const runs = [
      mkRun({ runId: "a", ruleIds: ["R_HEIGHT_75"] }),
      mkRun({ runId: "b", ruleIds: ["R_HEIGHT_75", "R_OTHER"] }),
      mkRun({ runId: "c", ruleIds: ["R_AREA_500"] }),
    ];
    const groups = useValidationRunsGrouping(runs, "rule");
    expect(groups.map((g) => g.groupKey)).toEqual(["R_AREA_500", "R_HEIGHT_75"]);
    expect(groups[1].runs.map((r) => r.runId)).toEqual(["a", "b"]);
  });

  it("places runs with empty ruleIds into __no_rule__ bucket LAST", () => {
    const runs = [
      mkRun({ runId: "a", ruleIds: [] }),
      mkRun({ runId: "b", ruleIds: ["R_X"] }),
    ];
    const groups = useValidationRunsGrouping(runs, "rule");
    expect(groups.map((g) => g.groupKey)).toEqual(["R_X", "__no_rule__"]);
    expect(groups[1].groupLabel).toBe("No Rule");
  });

  it("groups by state.stateId in state mode", () => {
    const runs = [
      mkRun({ runId: "a", state: { stateId: "S2", capturedAtUtc: null, parameterCount: 0 } }),
      mkRun({ runId: "b", state: { stateId: "S1", capturedAtUtc: null, parameterCount: 3 } }),
      mkRun({ runId: "c", state: { stateId: "S1", capturedAtUtc: null, parameterCount: 3 } }),
    ];
    const groups = useValidationRunsGrouping(runs, "state");
    expect(groups.map((g) => g.groupKey)).toEqual(["S1", "S2"]);
    expect(groups[0].runs.map((r) => r.runId).sort()).toEqual(["b", "c"]);
  });

  it("places runs with null state OR empty stateId into __no_state__ bucket LAST", () => {
    const runs = [
      mkRun({ runId: "a", state: null }),
      mkRun({ runId: "b", state: { stateId: "", capturedAtUtc: null, parameterCount: 0 } }),
      mkRun({ runId: "c", state: { stateId: "S1", capturedAtUtc: null, parameterCount: 0 } }),
    ];
    const groups = useValidationRunsGrouping(runs, "state");
    expect(groups.map((g) => g.groupKey)).toEqual(["S1", "__no_state__"]);
    expect(groups[1].groupLabel).toBe("No State");
    expect(groups[1].runs.map((r) => r.runId).sort()).toEqual(["a", "b"]);
  });

  it("orders runs within group by createdAt DESC, runId ASC tiebreak", () => {
    const runs = [
      mkRun({ runId: "older", ruleIds: ["R"], createdAt: "2026-04-01T10:00:00Z" }),
      mkRun({ runId: "newest", ruleIds: ["R"], createdAt: "2026-05-01T10:00:00Z" }),
      mkRun({ runId: "tieA", ruleIds: ["R"], createdAt: "2026-04-15T10:00:00Z" }),
      mkRun({ runId: "tieB", ruleIds: ["R"], createdAt: "2026-04-15T10:00:00Z" }),
    ];
    const groups = useValidationRunsGrouping(runs, "rule");
    expect(groups[0].runs.map((r) => r.runId)).toEqual(["newest", "tieA", "tieB", "older"]);
  });

  it("falls back to rule mode for unknown mode value", () => {
    const runs = [mkRun({ runId: "a", ruleIds: ["R_X"] })];
    const groups = useValidationRunsGrouping(runs, "garbage");
    expect(groups[0].groupKey).toBe("R_X");
  });

  it("treats invalid createdAt as epoch 0 (sorts last)", () => {
    const runs = [
      mkRun({ runId: "valid", ruleIds: ["R"], createdAt: "2026-05-01T10:00:00Z" }),
      mkRun({ runId: "broken", ruleIds: ["R"], createdAt: "not-a-date" }),
    ];
    const groups = useValidationRunsGrouping(runs, "rule");
    expect(groups[0].runs.map((r) => r.runId)).toEqual(["valid", "broken"]);
  });

  it("output is stable across repeated calls (no time-based randomness)", () => {
    const runs = [
      mkRun({ runId: "a", ruleIds: ["R_X"] }),
      mkRun({ runId: "b", ruleIds: ["R_X"] }),
    ];
    const g1 = useValidationRunsGrouping(runs, "rule");
    const g2 = useValidationRunsGrouping(runs, "rule");
    expect(JSON.stringify(g1)).toBe(JSON.stringify(g2));
  });
});
