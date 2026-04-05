# Project Overview

## What is Design Grammar System?

Design Grammar System (DG) automates architectural compliance checking by bridging natural language design rules to graph-based formal validation. The pipeline converts human-readable regulations (e.g. "maximum building height is 75 meters") into SWRL (Semantic Web Rule Language) ontology atoms stored in a Neo4j knowledge graph, then evaluates BIM geometry against these rules through a Grasshopper plugin, publishing color-coded pass/fail results to a Speckle 3D viewer.

## Problem Statement

Architects and urban planners verify designs against dozens or hundreds of regulatory constraints manually. This process is error-prone, time-consuming, and difficult to audit. Existing compliance tools are either too rigid (hardcoded rules) or require programming expertise to configure.

## Product Value

DG allows non-technical domain experts to define rules in natural language and immediately validate 3D models against them. The system provides visual feedback in the 3D viewport: green for compliant elements, red for violations, with drill-down to the specific rule that failed.

## Target Audience

- **Architects** validating designs against building codes and project requirements
- **Urban planners** checking compliance with zoning regulations
- **BIM managers** automating quality assurance workflows

## Core Pipeline

```
Natural Language Rule
  → LLM (Ollama/llama3.1) translates to SWRL atoms
    → SWRL atoms stored as Neo4j Cypher graph
      → Grasshopper plugin loads rules + binds geometry
        → Rule evaluator checks pass/fail
          → Results published to Speckle 3D overlay
```

## Current State (April 2026)

The system is functional with a multi-page SPA (Register → Home → Project → Graph Viewer / Model Viewer), two n8n workflows for rule ingestion and graph querying, a 5-component Grasshopper plugin, and Speckle-based validation visualization. Active work focuses on Model Viewer visual bugs, validation run management, and LLM accuracy improvements.
