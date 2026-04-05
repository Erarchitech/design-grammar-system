---
tags: [inbox, bug, model-viewer]
date: 2026-04-05
source: NOTES.txt
---

# Model Viewer Needs Rotation Fix and Validation Management

## From NOTES.txt

> Created Model Viewer integrated with Speckle locally hosted.  
> Next need to improve visualisation of the validation model viewport.  
> Now it shows mixed states as it would be rotated or smth else.  
> Also need to add option to delete and rename validations (management tool).  
> Also need to rebuild model viewer to be opened from Project page parallel with Graph Viewer.

## Issues

1. **Rotation/mixed state bug** — validation model viewport shows mixed orientation states
2. **Missing validation management** — no UI for deleting or renaming validation runs (delete endpoint exists in data-service, rename does not)
3. **Parallel view** — Model Viewer should open from ProjectPage alongside Graph Viewer, not as a replacement

## Status

Captured from developer notes. Not yet triaged.

## Related

- [[Model Viewer is a Vite-built Speckle 3D viewer]]
- [[Validation results publish to Speckle as overlay versions]]
- [[Current priorities]]
