import React from "react";
import { createRoot } from "react-dom/client";
import "./styles/styles.css";
// Select the restricted root BEFORE importing/mounting the normal App layers.
// A hash change reloads only when the #degram root slice changes; #degram-select announcements stay in this entry.
const degram = window.location.hash === "#degram";
window.addEventListener("hashchange", () => {
  if ((window.location.hash === "#degram") !== degram) window.location.reload();
});
const entry = degram ? import("./degram/DeGramWorkspace.jsx") : import("./App.jsx");
entry.then(({ default: Root }) => createRoot(document.getElementById("root")).render(<Root />));
