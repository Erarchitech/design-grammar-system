import React from "react";
import GraphEngine from "../graph/graphEngine.js";
import buildRings from "../graph/buildRings.js";
import Button from "../components/forms/Button.jsx";
import PropertiesTable from "../components/display/PropertiesTable.jsx";

// Presentation only: the existing engine owns layout/camera/selection. No API,
// editor callback, workflow/history import or persistent graph store here.
export default function ReadOnlyGraph({ graph }) {
  const canvas = React.useRef(null);
  const engine = React.useRef(null);
  const [selected, setSelected] = React.useState(null);
  const mapped = React.useMemo(() => buildRings(graph), [graph]);
  React.useEffect(() => {
    const view = new GraphEngine({ canvas: canvas.current }, {
      onSelect: ({ r, i }) => setSelected(mapped.rings[r].nodes[i]),
      onClearSel: () => setSelected(null)
    });
    engine.current = view;
    view.setData(mapped);
    view.idleDrift = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    view.setVisible(true);
    view.start({ thinkingAssets: false });
    return () => { view.stop(); engine.current = null; };
  }, [mapped]);
  return <>
    <canvas ref={canvas} className="degram-canvas" aria-label="Project graph" />
    <aside className="degram-panel degram-inspector" aria-label="Graph inspection">
      <h2>Nodes</h2>
      <div className="degram-nodes">
        {mapped.rings.flatMap((ring, r) => ring.nodes.map((node, i) =>
          <Button key={node.neoId} variant="outline" selected={selected?.neoId === node.neoId}
            onClick={() => engine.current?.selectNode(r, i, false)}>{node.label}</Button>
        ))}
        {graph.nodes.filter(node => !node.props.graph).map(node =>
          <Button key={node.id} variant="outline" onClick={() => {
            engine.current?.clearSel();
            setSelected({ neoId: node.id, label: node.props.label || node.props.name || String(node.id), kind: node.labels.join(" / "), props: Object.entries(node.props) });
          }}>{node.props.label || node.props.name || String(node.id)}</Button>
        )}
      </div>
      {graph.nodes.some(node => !node.props.graph) && <p>Nodes without a graph layer are not placed on graph rings.</p>}
      {selected ? <section aria-label="Node properties">
        <h2>{selected.label}</h2><p>{selected.kind}</p>
        <PropertiesTable editable={false} rows={selected.props.map(([key, value]) => ({ key, value: typeof value === "object" ? JSON.stringify(value) : String(value) }))} />
      </section> : <p>Select a node to inspect its properties.</p>}
    </aside>
  </>;
}
