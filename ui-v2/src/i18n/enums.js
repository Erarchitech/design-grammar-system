// Server enum words are always mapped through keys (D-13): the API sends `viewer`, `active`, never display text.
import { t } from "./index.js";

export const ROLE_VALUES = Object.freeze(["viewer", "editor", "owner"]);

export function roleLabel(role) {
  switch (role) {
    case "viewer":
      return t("Viewer");
    case "editor":
      return t("Editor");
    case "owner":
      return t("Owner");
    default:
      return String(role ?? "");
  }
}

export function connectorStatusLabel(status) {
  switch (status) {
    case "active":
      return t("On");
    case "never_connected":
      return t("Never connected");
    default:
      return t("Off");
  }
}
