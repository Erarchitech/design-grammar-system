import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    console.error("[DG-ErrorBoundary]", error, info?.componentStack);
  }
  render() {
    if (this.state.error) {
      return React.createElement("div", {
        style: { padding: 40, color: "#ffb0b1", background: "#0c1018", minHeight: "100vh", fontFamily: "sans-serif" }
      },
        React.createElement("h1", null, "Model Viewer Error"),
        React.createElement("pre", { style: { whiteSpace: "pre-wrap", color: "#98a4bd" } },
          String(this.state.error?.message || this.state.error)
        ),
        React.createElement("button", {
          onClick: () => this.setState({ error: null }),
          style: { marginTop: 16, padding: "8px 16px", cursor: "pointer" }
        }, "Retry")
      );
    }
    return this.props.children;
  }
}

window.addEventListener("error", (e) => console.error("[DG-WindowError]", e.error || e.message));
window.addEventListener("unhandledrejection", (e) => console.error("[DG-UnhandledRejection]", e.reason));

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
