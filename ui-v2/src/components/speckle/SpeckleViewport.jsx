import React from "react";
import {
  CameraController,
  DefaultViewerParams,
  FilteringExtension,
  SelectionExtension,
  SpeckleLoader,
  UpdateFlags,
  Viewer
} from "@speckle/viewer";
import { createProxyObjectLoader, parseViewerResource } from "../../lib/speckleProxy.js";
import { describeError, t } from "../../i18n/index.js";

// D-21 (Phase 1301-09): the stock SpeckleLoader keeps only the origin of its resource
// URL, takes a token and falls back to a stored one, so it could never go through the
// DG proxy without a credential. This subclass swaps only its object-loader factory for
// one that targets the project-authorised /speckle-proxy/ routes with the DG session
// cookie. It is never constructed with a token argument.
class ProxySpeckleLoader extends SpeckleLoader {
  initObjectLoader(resource, _ignoredCredential, _enableCaching, _resourceData, attributeMask, objectTypeMask) {
    return createProxyObjectLoader(resource, { attributeMask, objectTypeMask });
  }
}

// A persisted camera is restored only when every coordinate is a finite number.
function validCamera(cam) {
  const ok = (v) => v && [v.x, v.y, v.z].every((n) => typeof n === "number" && Number.isFinite(n));
  return cam && ok(cam.position) && ok(cam.target) ? { position: cam.position, target: cam.target } : null;
}

function sameCamera(a, b) {
  if (!a || !b) return false;
  return ["position", "target"].every((k) => ["x", "y", "z"].every((c) => Math.abs(a[k][c] - b[k][c]) < 1e-6));
}

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

  // Phase 1303-15: the model context of a check (walls, columns, beams of the rule's classes) ships in the
  // validation version as neutral dgContext objects, never coloured as passed or failed.
  const contextObjectIds = [];
  for (const node of worldTree.findAll((n) => n.model?.raw?.dgContext === true)) {
    const ids = collectAllDescendantIds(node);
    contextObjectIds.push(...(ids.length > 0 ? ids : [node.model.id]));
  }

  return {
    entityMap,
    allValidationObjectIds: Array.from(new Set(allValidationObjectIds)),
    contextObjectIds: Array.from(new Set(contextObjectIds))
  };
}

/**
 * SpeckleViewport — wraps @speckle/viewer Viewer into a controlled React component.
 *
 * Props:
 *   resourceUrls    — DG-proxy object URLs from the view payload (view.viewerResources) that
 *                     should be in the scene now; the browser holds no Speckle credential,
 *                     geometry is read through the project-authorised /speckle-proxy/ routes
 *                     with the session cookie. Changing the set loads/unloads only the
 *                     difference (a run switch swaps only the validation model).
 *   project         — DG project name for world tree entity mapping
 *   runId           — Validation run ID for world tree entity mapping
 *   failedEntityIds — dgEntityIds of failing entities (colored failColor)
 *   passedEntityIds — dgEntityIds of passing entities (colored passColor)
 *   showFailed / showPassed — visibility toggles (toolbar checkboxes)
 *   failColor / passColor — hex colors for the validation overlay
 *   failOpacity / passOpacity — 0..100 opacity for each group
 *   contextColor / contextOpacity — color and 0..100 opacity of the model context (dgContext objects)
 *   hiddenIds       — dgEntityIds hidden via the Hide button
 *   isolateEntityId — when set, isolates that single entity
 *   viewMode        — "3d" (perspective orbit) or "map" (top-down orthographic)
 *   onEntityClick   — Called with (dgEntityId) when a Speckle geometry object is clicked
 *   onReady         — Called after each resource sync completes (first load, run switch)
 *   onViewChanged   — Called when the camera settles after a move (thumbnail refresh)
 *   initialCamera   — { position: {x,y,z}, target: {x,y,z} } to open the first load at,
 *                     instead of zooming to fit (the architect's last viewpoint)
 *   onCameraChange  — Called with { position, target } when the 3D camera settles on a
 *                     loaded scene (not in map mode); the caller persists it
 *   onError         — Called with (message) on initialization failure
 *   apiRef          — Optional React ref; receives { screenshot(), sceneRunId() } once the
 *                     viewer exists; sceneRunId() is null while resources are swapping
 *   style           — Optional container styling; defaults to { position: "absolute", inset: 0 }
 */
export default function SpeckleViewport({
  resourceUrls,
  project,
  runId,
  failedEntityIds,
  passedEntityIds,
  showFailed = true,
  showPassed = true,
  failColor = "#e7000b",
  passColor = "#737373",
  failOpacity = 85,
  passOpacity = 55,
  contextColor = "#a3a3a3",
  contextOpacity = 35,
  hiddenIds,
  isolateEntityId = null,
  viewMode = "3d",
  onEntityClick,
  onReady,
  onViewChanged,
  initialCamera = null,
  onCameraChange,
  onError,
  apiRef,
  style
}) {
  const hostRef = React.useRef(null);
  const viewerRef = React.useRef(null);
  const filteringRef = React.useRef(null);
  const entityMapRef = React.useRef(new Map());
  const allValidationObjectIdsRef = React.useRef([]);
  const contextObjectIdsRef = React.useRef([]);
  const loadedUrlsRef = React.useRef([]); // resource URLs currently in the scene
  const hasLoadedRef = React.useRef(false); // this viewer has loaded geometry before
  const syncQueueRef = React.useRef(Promise.resolve()); // serialises load/unload jobs
  const sceneRunIdRef = React.useRef(null); // run the loaded scene shows; null while syncing
  const onEntityClickRef = React.useRef(onEntityClick);
  const onReadyRef = React.useRef(onReady);
  const onErrorRef = React.useRef(onError);
  const onViewChangedRef = React.useRef(onViewChanged);
  const onCameraChangeRef = React.useRef(onCameraChange);
  const initialCameraRef = React.useRef(initialCamera); // read once, at the first load
  const viewModeRef = React.useRef(viewMode);
  const reportCameraRef = React.useRef(null);
  const removeInteractionListenersRef = React.useRef(null);
  const [viewerReady, setViewerReady] = React.useState(false);
  const [fitted, setFitted] = React.useState(false); // first load framed the camera
  const [sceneTick, setSceneTick] = React.useState(0); // bumps after every completed sync

  // Keep callback refs current (effect uses refs to avoid re-running on callback reference changes)
  onEntityClickRef.current = onEntityClick;
  onReadyRef.current = onReady;
  onErrorRef.current = onError;
  onViewChangedRef.current = onViewChanged;
  onCameraChangeRef.current = onCameraChange;
  viewModeRef.current = viewMode;

  // Viewer lifecycle — one viewer per mount. Run switches only load/unload
  // resources (below), so the camera survives them.
  React.useEffect(() => {
    let disposed = false;
    const host = hostRef.current;
    if (!host) return undefined;

    const initViewer = async () => {
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

      const camera = viewer.createExtension(CameraController);
      viewer.createExtension(SelectionExtension);
      filteringRef.current = viewer.createExtension(FilteringExtension);

      // Report the camera after the architect moves it. CameraEvent.Stationary
      // is not emitted by this @speckle/viewer build (only Dynamic is), and
      // pointer events miss drags released outside the canvas, keyboard moves
      // and inertia — so the camera is polled: once it holds still for a tick
      // and differs from the last report, it is reported. getPosition() and
      // getTarget() return the controls' goal, so the value is final even while
      // damping still eases the view.
      // Only a 3D view of a loaded scene is worth keeping: while resources swap
      // the camera may sit at its default, and map mode is a fixed top-down
      // projection.
      const cameraReportable = () => !disposed && sceneRunIdRef.current && viewModeRef.current !== "map";
      const readCamera = () => {
        const p = camera.getPosition();
        const t = camera.getTarget();
        return { position: { x: p.x, y: p.y, z: p.z }, target: { x: t.x, y: t.y, z: t.z } };
      };
      let seen = null;
      let reported = null;
      const reportCamera = () => {
        if (!cameraReportable()) return;
        reported = readCamera();
        onCameraChangeRef.current?.(reported);
      };
      reportCameraRef.current = reportCamera;
      const poll = setInterval(() => {
        if (!cameraReportable()) {
          seen = null;
          return;
        }
        const current = readCamera();
        if (!sameCamera(current, seen)) {
          seen = current; // still moving, or just changed — wait one more tick
          return;
        }
        if (sameCamera(current, reported)) return;
        reportCamera();
        onViewChangedRef.current?.(); // tile thumbnails follow the new view
      }, 600);
      window.addEventListener("pagehide", reportCamera);
      removeInteractionListenersRef.current = () => {
        clearInterval(poll);
        window.removeEventListener("pagehide", reportCamera);
      };

      viewer.on("object-clicked", (payload) => {
        const hit = payload?.hits?.[0];
        const raw = hit?.node?.model?.raw || {};
        const dgEntityId = raw.dgEntityId || "";
        if (dgEntityId && onEntityClickRef.current) {
          onEntityClickRef.current(dgEntityId);
        }
      });

      if (apiRef) {
        apiRef.current = {
          screenshot: () => viewer.screenshot(),
          // Run id of the scene on screen, or null while resources are swapping —
          // a thumbnail is filed under the run it actually shows.
          sceneRunId: () => sceneRunIdRef.current
        };
      }

      setViewerReady(true);
    };

    void initViewer().catch((err) => {
      if (!disposed) {
        onErrorRef.current?.(describeError(err, t("Speckle viewer initialization failed")));
      }
    });

    return () => {
      reportCameraRef.current?.(); // keep the last viewpoint when the viewer unmounts
      reportCameraRef.current = null;
      removeInteractionListenersRef.current?.();
      removeInteractionListenersRef.current = null;
      disposed = true;
      setViewerReady(false);
      setFitted(false);
      if (apiRef) apiRef.current = null;
      if (viewerRef.current) {
        viewerRef.current.dispose();
        viewerRef.current = null;
      }
      filteringRef.current = null;
      entityMapRef.current = new Map();
      allValidationObjectIdsRef.current = [];
      contextObjectIdsRef.current = [];
      loadedUrlsRef.current = [];
      hasLoadedRef.current = false;
      sceneRunIdRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Resource sync — keyed on the joined resource-url string (scalar), not the
  // array identity. Unloads what left the set and loads what joined it. An
  // unloaded model takes its geometry AND its baked ground shadow with it
  // (removeRenderTree re-bakes the shadowcatcher); hiding it through the
  // FilteringExtension would leave the shadow behind.
  const resourceKey = (resourceUrls || []).filter(Boolean).join("|");
  React.useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewerReady || !viewer) return undefined;
    const urls = resourceKey ? resourceKey.split("|") : [];
    if (urls.some((url) => !parseViewerResource(url))) {
      onErrorRef.current?.(t("Unexpected geometry resource URL"));
      return undefined;
    }

    let stale = false;
    sceneRunIdRef.current = null;
    const job = async () => {
      if (stale || viewerRef.current !== viewer) return;
      const leaving = loadedUrlsRef.current.filter((url) => !urls.includes(url));
      for (const url of leaving) {
        await viewer.unloadObject(url);
        loadedUrlsRef.current = loadedUrlsRef.current.filter((u) => u !== url);
      }
      // The server already resolved model/version to a concrete object URL
      // (speckle_proxy.resolve_view_resources); no Speckle GraphQL call and no
      // token ever happens in the browser. Only the very first load frames the
      // camera — at the saved viewpoint when there is one, else zoomed to fit;
      // later loads keep the architect's viewpoint.
      // "First" means first for this viewer, not "the scene is empty": a run
      // switch unloads the old validation model before loading the new one, and
      // judging by the empty scene re-framed the camera on every switch.
      const firstLoad = !hasLoadedRef.current;
      const saved = firstLoad ? validCamera(initialCameraRef.current) : null;
      const frame = firstLoad && !saved;
      for (const url of urls) {
        if (stale || viewerRef.current !== viewer) return;
        if (loadedUrlsRef.current.includes(url)) continue;
        const loader = new ProxySpeckleLoader(viewer.getWorldTree(), url);
        await viewer.loadObject(loader, frame);
        loadedUrlsRef.current = loadedUrlsRef.current.concat([url]);
        hasLoadedRef.current = true;
      }
      if (stale || viewerRef.current !== viewer) return;
      if (saved && urls.length > 0) {
        viewer.getExtension(CameraController)?.setCameraView(saved, false);
        initialCameraRef.current = null;
      }

      // Entity mapping: walk the world tree to collect dgEntityId -> objectId[] mapping
      const worldTree = viewer.getWorldTree();
      const collected = collectValidationObjects(worldTree, runId, project);
      entityMapRef.current = collected.entityMap;
      allValidationObjectIdsRef.current = collected.allValidationObjectIds;
      contextObjectIdsRef.current = collected.contextObjectIds;

      // Debug handle for live world-tree inspection (harmless in production)
      window.__dgSpeckleDebug = { viewer, worldTree, runId, project, entityMap: collected.entityMap };

      viewer.requestRender(UpdateFlags.RENDER_RESET | UpdateFlags.SHADOWS);
      sceneRunIdRef.current = runId || null;
      if (urls.length > 0) setFitted(true);
      setSceneTick((t) => t + 1);
      onReadyRef.current?.();
    };

    syncQueueRef.current = syncQueueRef.current.then(job).catch((err) => {
      if (!stale) onErrorRef.current?.(describeError(err, t("Speckle geometry failed to load")));
    });
    return () => {
      stale = true;
    };
  }, [viewerReady, resourceKey, project, runId]);

  // Validation overlay — visibility, isolation, hiding, coloring and opacity.
  // Ported from the legacy viewer (graph-viewer/model-viewer/src/App.jsx):
  // geometry ships grey from Speckle; the fail/pass color coding is applied
  // client-side through the FilteringExtension + renderer material overrides.
  React.useEffect(() => {
    const viewer = viewerRef.current;
    const filtering = filteringRef.current;
    if (!sceneTick || !viewer || !filtering) return;

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
    } else {
      // Hide only the excluded validation objects + Hide-button picks
      const visibleSet = new Set(visibleObjectIds);
      const hideSet = new Set(
        allValidationObjectIdsRef.current.filter((id) => !visibleSet.has(id))
      );
      for (const id of hideButtonIds) hideSet.add(id);
      if (hideSet.size > 0) {
        filtering.hideObjects([...hideSet], "dg-vis", true, false);
      }
    }

    // Colour/material groups exclude Hide-button picks: renderer.setMaterial
    // below is a raw override that would resurrect hidden geometry otherwise.
    // Under single-entity isolation, only that entity keeps its overlay.
    const isoSet = isolateEntityId ? new Set(flatten([isolateEntityId])) : null;
    const overlayVisible = (id) => !hideButtonIds.has(id) && (!isoSet || isoSet.has(id));
    const failedVisibleIds = failedObjectIds.filter(overlayVisible);
    const passedVisibleIds = passedObjectIds.filter(overlayVisible);
    const contextVisibleIds = contextObjectIdsRef.current.filter(overlayVisible);
    const colorGroups = [];
    if (failedVisibleIds.length > 0) colorGroups.push({ objectIds: failedVisibleIds, color: failColor });
    if (passedVisibleIds.length > 0) colorGroups.push({ objectIds: passedVisibleIds, color: passColor });
    if (contextVisibleIds.length > 0) colorGroups.push({ objectIds: contextVisibleIds, color: contextColor });
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
      applyGroupMaterial(contextVisibleIds, contextColor, contextOpacity);
    } catch {
      // renderer material override unavailable — color groups still applied
    }

    viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS);
  }, [
    sceneTick,
    failedEntityIds,
    passedEntityIds,
    showFailed,
    showPassed,
    failColor,
    passColor,
    failOpacity,
    passOpacity,
    contextColor,
    contextOpacity,
    hiddenIds,
    isolateEntityId
  ]);

  // View mode — "map" is a top-down orthographic projection of the real
  // model (no more synthetic boxes); "3d" restores the perspective orbit.
  React.useEffect(() => {
    const viewer = viewerRef.current;
    if (!fitted || !viewer) return;
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
  }, [fitted, viewMode]);

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
