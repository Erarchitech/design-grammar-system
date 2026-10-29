import React from "react";
import "./model-panels.css";

export function fitModelPanels(width, requested) {
  const available = Math.max(0, width - Math.min(240, width * 0.4));
  const total = requested.left + requested.right;
  const scale = total > available ? available / total : 1;
  return { left: requested.left * scale, right: requested.right * scale };
}

export default function useModelPanels(rootRef) {
  const [requested, setRequested] = React.useState({ left: 320, right: 344 });
  const [containerWidth, setContainerWidth] = React.useState(0);
  const drag = React.useRef(null);
  React.useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const measure = () => setContainerWidth(root.getBoundingClientRect().width);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    return () => observer.disconnect();
  }, [rootRef]);
  const widths = containerWidth ? fitModelPanels(containerWidth, requested) : requested;
  const resize = (side, width) => {
    const other = side === "left" ? "right" : "left";
    const maximum = Math.max(0, containerWidth - widths[other] - Math.min(240, containerWidth * 0.4));
    const minimum = Math.min(side === "left" ? 220 : 240, maximum);
    setRequested({ ...widths, [side]: Math.max(minimum, Math.min(560, maximum, width)) });
  };
  const handle = side => ({
    className: "dg-model-panel-resizer",
    role: "separator",
    tabIndex: 0,
    "aria-orientation": "vertical",
    "aria-valuenow": Math.round(widths[side]),
    "aria-valuemin": 0,
    "aria-valuemax": 560,
    onPointerDown(event) {
      if (event.button !== 0) return;
      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = { side, x: event.clientX, width: widths[side] };
    },
    onPointerMove(event) {
      if (drag.current?.side !== side) return;
      resize(side, drag.current.width + (event.clientX - drag.current.x) * (side === "left" ? 1 : -1));
    },
    onPointerUp(event) {
      drag.current = null;
      if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    },
    onPointerCancel() { drag.current = null; },
    onLostPointerCapture() { drag.current = null; },
    onKeyDown(event) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      resize(side, widths[side] + (event.key === "ArrowRight" ? 16 : -16) * (side === "left" ? 1 : -1));
    },
    style: { position: "absolute", zIndex: 20, top: 0, bottom: 0, [side === "left" ? "right" : "left"]: -4, width: 9, cursor: "col-resize", touchAction: "none", background: "transparent" }
  });
  return { widths, handle };
}
