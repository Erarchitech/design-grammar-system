import React from "react";
import {
  CameraController,
  DefaultViewerParams,
  FilteringExtension,
  SelectionExtension,
  SpeckleLoader,
  UpdateFlags,
  UrlHelper,
  Viewer
} from "@speckle/viewer";

function collectAllDescendantIds(node) {
  const ids = [];
  node.walk((child) => {
    if (child.model?.id) ids.push(child.model.id);
    return true;
  });
  return ids;
}

function collectValidationObjects(worldTree, runId, project) {
  const entityMap = new Map();
  const allValidationObjectIds = [];

  // Debug: sample some tree nodes to see their structure
  let sampleCount = 0;
  worldTree.walk((node) => {
    if (sampleCount < 10 && node.model?.raw && Object.keys(node.model.raw).length > 2) {
      console.log("[DG-Debug] Sample tree node:", node.model.id, Object.keys(node.model.raw));
      sampleCount++;
    }
    return true;
  });

  // Primary search: strict match on project + run + entity id.
  let nodes = worldTree.findAll((node) => {
    const raw = node.model?.raw;
    return raw && raw.validationRunId === runId && raw.dgProject === project && raw.dgEntityId;
  });

  console.log("[DG-Debug] collectValidationObjects: runId =", runId, "project =", project, "matched nodes =", nodes.length);

  // Legacy fallback: some historical payloads may miss validationRunId.
  if (nodes.length === 0) {
    nodes = worldTree.findAll((node) => {
      const raw = node.model?.raw;
      return raw && raw.dgProject === project && raw.dgEntityId;
    });
    console.log("[DG-Debug] Fallback search (project + dgEntityId): matched nodes =", nodes.length);
  }

  // Final fallback for older data where project was not persisted in object raw payload.
  if (nodes.length === 0) {
    nodes = worldTree.findAll((node) => {
      const raw = node.model?.raw;
      return raw && raw.validationRunId === runId && raw.dgEntityId;
    });
    console.log("[DG-Debug] Fallback search (runId + dgEntityId): matched nodes =", nodes.length);
  }

  for (const node of nodes) {
    const dgEntityId = node.model.raw.dgEntityId;
    const objectId = node.model.id;
    if (!dgEntityId || !objectId) continue;

    const allIds = collectAllDescendantIds(node);
    if (allIds.length === 0) allIds.push(objectId);

    allValidationObjectIds.push(...allIds);
    if (!entityMap.has(dgEntityId)) {
      entityMap.set(dgEntityId, []);
    }
    entityMap.get(dgEntityId).push(...allIds);
  }

  console.log("[DG-Debug] entityMap size:", entityMap.size, "total objectIds:", allValidationObjectIds.length);
  if (entityMap.size > 0) {
    const first = entityMap.entries().next().value;
    console.log("[DG-Debug] Sample entity:", first[0], "→", first[1].length, "objectIds:", first[1].slice(0, 3));
  }

  return {
    entityMap,
    allValidationObjectIds: Array.from(new Set(allValidationObjectIds))
  };
}

/**
 * SpeckleViewport — wraps @speckle/viewer Viewer into a controlled React component.
 *
 * Props:
 *   readToken       — Speckle read token from the view payload (NOT stored in UI env vars)
 *   resourceUrls    — Speckle resource URLs (typically [view.baseResourceUrl, view.validationResourceUrl])
 *   project         — DG project name for world tree entity mapping
 *   runId           — Validation run ID for world tree entity mapping
 *   failedEntityIds — dgEntityIds of failing entities (colored failColor)
 *   passedEntityIds — dgEntityIds of passing entities (colored passColor)
 *   showFailed / showPassed / showBase — visibility toggles (toolbar checkboxes)
 *   failColor / passColor — hex colors for the validation overlay
 *   failOpacity / passOpacity — 0..100 opacity for each group
 *   hiddenIds       — dgEntityIds hidden via the Hide button
 *   isolateEntityId — when set, isolates that single entity
 *   viewMode        — "3d" (perspective orbit) or "map" (top-down orthographic)
 *   onEntityClick   — Called with (dgEntityId) when a Speckle geometry object is clicked
 *   onReady         — Called after viewer finishes loading all resources
 *   onError         — Called with (message) on initialization failure
 *   apiRef          — Optional React ref; receives { screenshot() } once ready
 *   style           — Optional container styling; defaults to { position: "absolute", inset: 0 }
 */
export default function SpeckleViewport({
  readToken,
  resourceUrls,
  project,
  runId,
  failedEntityIds,
  passedEntityIds,
  showFailed = true,
  showPassed = true,
  showBase = true,
  failColor = "#e7000b",
  passColor = "#737373",
  failOpacity = 85,
  passOpacity = 55,
  hiddenIds,
  isolateEntityId = null,
  viewMode = "3d",
  onEntityClick,
  onReady,
  onError,
  apiRef,
  style
}) {
  const hostRef = React.useRef(null);
  const viewerRef = React.useRef(null);
  const filteringRef = React.useRef(null);
  const entityMapRef = React.useRef(new Map());
  const allValidationObjectIdsRef = React.useRef([]);
  const disposedRef = React.useRef(false);
  const clickHandlerRef = React.useRef(null);
  const onEntityClickRef = React.useRef(onEntityClick);
  const onReadyRef = React.useRef(onReady);
  const onErrorRef = React.useRef(onError);
  const [ready, setReady] = React.useState(false);

  // Keep callback refs current (effect uses refs to avoid re-running on callback reference changes)
  onEntityClickRef.current = onEntityClick;
  onReadyRef.current = onReady;
  onErrorRef.current = onError;

  // Viewer lifecycle — keyed on the joined resource-url string (scalar), not
  // the array identity: ModelScreen re-renders must never recreate the viewer.
  const resourceKey = (resourceUrls || []).filter(Boolean).join("|");
  React.useEffect(() => {
    const urls = resourceKey ? resourceKey.split("|") : [];
    if (urls.length === 0 || !readToken) {
      onErrorRef.current?.("No Speckle resource URLs or token available");
      return;
    }

    let disposed = false;
    disposedRef.current = false;
    setReady(false);

    const initViewer = async () => {
      // Dispose previous viewer if it exists
      if (viewerRef.current) {
        viewerRef.current.dispose();
        viewerRef.current = null;
        filteringRef.current = null;
      }
      const host = hostRef.current;
      if (!host) return;
      while (host.firstChild) {
        host.removeChild(host.firstChild);
      }

      try {
        const viewer = new Viewer(host, {
          ...DefaultViewerParams,
          verbose: false,
          showStats: false
        });
        viewerRef.current = viewer;
        await viewer.init();

        if (disposed) {
          viewer.dispose();
          if (viewerRef.current === viewer) viewerRef.current = null;
          return;
        }

        viewer.createExtension(CameraController);
        viewer.createExtension(SelectionExtension);
        filteringRef.current = viewer.createExtension(FilteringExtension);

        // Load each resource
        for (const resourceUrl of urls) {
          if (disposed) return;
          const concreteUrls = await UrlHelper.getResourceUrls(resourceUrl);
          for (const url of concreteUrls) {
            if (disposed) return;
            const loader = new SpeckleLoader(viewer.getWorldTree(), url, readToken);
            await viewer.loadObject(loader, true);
          }
        }

        if (disposed) return;

        // Entity mapping: walk the world tree to collect dgEntityId -> objectId[] mapping
        const worldTree = viewer.getWorldTree();
        const collected = collectValidationObjects(worldTree, runId, project);
        entityMapRef.current = collected.entityMap;
        allValidationObjectIdsRef.current = collected.allValidationObjectIds;

        // Debug handle for live world-tree inspection (harmless in production)
        window.__dgSpeckleDebug = { viewer, worldTree, runId, project, entityMap: collected.entityMap };

        // Click handler
        const handleClick = (payload) => {
          const hit = payload?.hits?.[0];
          const raw = hit?.node?.model?.raw || {};
          const dgEntityId = raw.dgEntityId || "";
          if (dgEntityId && onEntityClickRef.current) {
            onEntityClickRef.current(dgEntityId);
          }
        };
        clickHandlerRef.current = handleClick;
        viewer.on("object-clicked", handleClick);

        if (apiRef) {
          apiRef.current = {
            screenshot: () => viewer.screenshot()
          };
        }

        setReady(true);
        onReadyRef.current?.();
      } catch (err) {
        if (!disposed) {
          onErrorRef.current?.(err.message || "Speckle viewer initialization failed");
        }
      }
    };

    void initViewer().catch((err) => {
      if (!disposed) {
        onErrorRef.current?.(err.message || "Speckle viewer initialization failed");
      }
    });

    return () => {
      disposed = true;
      disposedRef.current = true;
      setReady(false);
      if (apiRef) apiRef.current = null;
      if (viewerRef.current) {
        if (clickHandlerRef.current && typeof viewerRef.current.off === "function") {
          viewerRef.current.off("object-clicked", clickHandlerRef.current);
        }
        clickHandlerRef.current = null;
        viewerRef.current.dispose();
        viewerRef.current = null;
      }
      filteringRef.current = null;
      entityMapRef.current = new Map();
      allValidationObjectIdsRef.current = [];
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resourceKey, readToken, project, runId]);

  // Validation overlay — visibility, isolation, hiding, coloring and opacity.
  // Ported from the legacy viewer (graph-viewer/model-viewer/src/App.jsx):
  // geometry ships grey from Speckle; the fail/pass color coding is applied
  // client-side through the FilteringExtension + renderer material overrides.
  React.useEffect(() => {
    const viewer = viewerRef.current;
    const filtering = filteringRef.current;
    if (!ready || !viewer || !filtering) return;

    const entityMap = entityMapRef.current;
    const flatten = (ids) => {
      const objectIds = [];
      for (const id of ids || []) {
        const mapped = entityMap.get(id) || [];
        objectIds.push(...mapped);
      }
      return Array.from(new Set(objectIds));
    };

    filtering.resetFilters();
    const failedObjectIds = showFailed ? flatten(failedEntityIds) : [];
    const passedObjectIds = showPassed ? flatten(passedEntityIds) : [];
    const hideButtonIds = new Set(flatten(hiddenIds));
    const visibleObjectIds = [...failedObjectIds, ...passedObjectIds].filter((id) => !hideButtonIds.has(id));

    // FilteringExtension keeps a SINGLE visibility state — a second
    // hideObjects/isolateObjects call with a different stateKey wipes the
    // first one. So the toggles must resolve to exactly ONE operation here.
    if (isolateEntityId) {
      const isoObjectIds = flatten([isolateEntityId]);
      if (isoObjectIds.length > 0) {
        filtering.isolateObjects(isoObjectIds, "dg-vis", true, true);
      }
    } else if (showBase) {
      // Base visible → hide only the excluded validation objects + Hide-button picks
      const visibleSet = new Set(visibleObjectIds);
      const hideSet = new Set(
        allValidationObjectIdsRef.current.filter((id) => !visibleSet.has(id))
      );
      for (const id of hideButtonIds) hideSet.add(id);
      if (hideSet.size > 0) {
        filtering.hideObjects([...hideSet], "dg-vis", true, false);
      }
    } else if (visibleObjectIds.length > 0) {
      // Base hidden → isolate the visible validation objects (hides the rest)
      filtering.isolateObjects(visibleObjectIds, "dg-vis", true, false);
    } else {
      // Everything toggled off → isolate a sentinel id nothing matches,
      // which hides the entire scene (empty ids would reset to show-all).
      filtering.isolateObjects(["dg-none"], "dg-vis", true, false);
    }

    // Colour/material groups exclude Hide-button picks: renderer.setMaterial
    // below is a raw override that would resurrect hidden geometry otherwise.
    // Under single-entity isolation, only that entity keeps its overlay.
    const isoSet = isolateEntityId ? new Set(flatten([isolateEntityId])) : null;
    const overlayVisible = (id) => !hideButtonIds.has(id) && (!isoSet || isoSet.has(id));
    const failedVisibleIds = failedObjectIds.filter(overlayVisible);
    const passedVisibleIds = passedObjectIds.filter(overlayVisible);
    const colorGroups = [];
    if (failedVisibleIds.length > 0) colorGroups.push({ objectIds: failedVisibleIds, color: failColor });
    if (passedVisibleIds.length > 0) colorGroups.push({ objectIds: passedVisibleIds, color: passColor });
    if (colorGroups.length > 0) {
      filtering.setUserObjectColors(colorGroups);
    }

    // Per-group opacity via renderer material overrides. setUserObjectColors
    // only handles RGB (the Speckle ramp texture has no alpha), so resolve
    // each group's objectIds to render views and set a material with opacity.
    try {
      const renderer = viewer.getRenderer();
      const worldTree = viewer.getWorldTree();
      const renderTree = worldTree.getRenderTree();

      const applyGroupMaterial = (objectIds, hexColor, opacityPercent) => {
        if (objectIds.length === 0) return;
        const rvs = [];
        for (const id of objectIds) {
          const nodes = worldTree.findId(id);
          if (nodes) {
            for (const node of nodes) {
              const views = renderTree.getRenderViewsForNode(node);
              if (views) rvs.push(...views);
            }
          }
        }
        if (rvs.length === 0) return;
        const colorInt = parseInt(hexColor.slice(1), 16);
        renderer.setMaterial(rvs, {
          id: `dg-${hexColor}-${opacityPercent}`,
          color: colorInt,
          emissive: 0,
          opacity: opacityPercent / 100,
          roughness: 0.6,
          metalness: 0,
          vertexColors: false,
          lineWeight: 1
        });
      };

      applyGroupMaterial(failedVisibleIds, failColor, failOpacity);
      applyGroupMaterial(passedVisibleIds, passColor, passOpacity);
    } catch {
      // renderer material override unavailable — color groups still applied
    }

    viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS);
  }, [
    ready,
    failedEntityIds,
    passedEntityIds,
    showFailed,
    showPassed,
    showBase,
    failColor,
    passColor,
    failOpacity,
    passOpacity,
    hiddenIds,
    isolateEntityId
  ]);

  // View mode — "map" is a top-down orthographic projection of the real
  // model (no more synthetic boxes); "3d" restores the perspective orbit.
  React.useEffect(() => {
    const viewer = viewerRef.current;
    if (!ready || !viewer) return;
    const cam = viewer.getExtension(CameraController);
    if (!cam) return;
    try {
      if (viewMode === "map") {
        if (typeof cam.setOrthoCameraOn === "function") cam.setOrthoCameraOn();
        if (typeof cam.setCameraView === "function") cam.setCameraView("top", true);
      } else {
        if (typeof cam.setPerspectiveCameraOn === "function") cam.setPerspectiveCameraOn();
      }
      viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS);
    } catch {
      // camera API drift across @speckle/viewer versions — keep current view
    }
  }, [ready, viewMode]);

  // Resize handling
  React.useEffect(() => {
    const host = hostRef.current;
    if (!host || typeof ResizeObserver === "undefined") return undefined;

    const observer = new ResizeObserver(() => {
      const viewer = viewerRef.current;
      if (viewer && typeof viewer.resize === "function") {
        viewer.resize();
        if (typeof viewer.requestRender === "function") {
          viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS);
        }
      }
    });
    observer.observe(host);
    return () => observer.disconnect();
  }, []);

  return (
    <div style={style || { position: "absolute", inset: 0 }}>
      <div
        ref={hostRef}
        style={{ width: "100%", height: "100%", position: "absolute", inset: 0 }}
      />
    </div>
  );
}
