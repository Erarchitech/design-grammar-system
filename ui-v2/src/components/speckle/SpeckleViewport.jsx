import React from "react";
import {
  CameraController,
  DefaultViewerParams,
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

  // Primary search: strict match on project + run + entity id.
  let nodes = worldTree.findAll((node) => {
    const raw = node.model?.raw;
    return raw && raw.validationRunId === runId && raw.dgProject === project && raw.dgEntityId;
  });

  // Legacy fallback: some historical payloads may miss validationRunId.
  if (nodes.length === 0) {
    nodes = worldTree.findAll((node) => {
      const raw = node.model?.raw;
      return raw && raw.dgProject === project && raw.dgEntityId;
    });
  }

  // Final fallback for older data where project was not persisted in object raw payload.
  if (nodes.length === 0) {
    nodes = worldTree.findAll((node) => {
      const raw = node.model?.raw;
      return raw && raw.validationRunId === runId && raw.dgEntityId;
    });
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

  return {
    entityMap,
    allValidationObjectIds: Array.from(new Set(allValidationObjectIds))
  };
}

/**
 * SpeckleViewport — wraps @speckle/viewer Viewer into a controlled React component.
 *
 * Props:
 *   readToken     — Speckle read token from the view payload (NOT stored in UI env vars)
 *   resourceUrls  — Speckle resource URLs (typically [view.baseResourceUrl, view.validationResourceUrl])
 *   project       — DG project name for world tree entity mapping
 *   runId         — Validation run ID for world tree entity mapping
 *   onEntityClick — Called with (dgEntityId) when a Speckle geometry object is clicked
 *   onReady       — Called after viewer finishes loading all resources
 *   onError       — Called with (message) on initialization failure
 *   style         — Optional container styling; defaults to { position: "absolute", inset: 0 }
 */
export default function SpeckleViewport({
  readToken,
  resourceUrls,
  project,
  runId,
  onEntityClick,
  onReady,
  onError,
  style
}) {
  const hostRef = React.useRef(null);
  const viewerRef = React.useRef(null);
  const entityMapRef = React.useRef(new Map());
  const disposedRef = React.useRef(false);
  const clickHandlerRef = React.useRef(null);

  // Viewer lifecycle — keyed on resourceUrls + readToken + project + runId
  React.useEffect(() => {
    const urls = resourceUrls?.filter(Boolean) || [];
    if (urls.length === 0 || !readToken) {
      onError?.("No Speckle resource URLs or token available");
      return;
    }

    let disposed = false;
    disposedRef.current = false;

    const initViewer = async () => {
      // Dispose previous viewer if it exists
      if (viewerRef.current) {
        viewerRef.current.dispose();
        viewerRef.current = null;
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
        await viewer.init();

        if (disposed) {
          viewer.dispose();
          return;
        }

        viewer.createExtension(CameraController);
        viewer.createExtension(SelectionExtension);
        viewerRef.current = viewer;

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

        // Click handler
        const handleClick = (payload) => {
          const hit = payload?.hits?.[0];
          const raw = hit?.node?.model?.raw || {};
          const dgEntityId = raw.dgEntityId || "";
          if (dgEntityId && onEntityClick) {
            onEntityClick(dgEntityId);
          }
        };
        clickHandlerRef.current = handleClick;
        viewer.on("object-clicked", handleClick);

        onReady?.();
      } catch (err) {
        if (!disposed) {
          onError?.(err.message || "Speckle viewer initialization failed");
        }
      }
    };

    void initViewer();

    return () => {
      disposed = true;
      disposedRef.current = true;
      if (viewerRef.current) {
        if (clickHandlerRef.current && typeof viewerRef.current.off === "function") {
          viewerRef.current.off("object-clicked", clickHandlerRef.current);
        }
        clickHandlerRef.current = null;
        viewerRef.current.dispose();
        viewerRef.current = null;
      }
      entityMapRef.current = new Map();
    };
  }, [resourceUrls, readToken, project, runId, onEntityClick, onReady, onError]);

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
