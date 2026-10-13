import React from "react";
import { Button, Input, Select, Badge } from "../components/index.js";
import { getSettings, saveSettings, testConnection, fetchModels } from "../lib/llmApi.js";
import { describeError } from "../i18n/index.js";
import { useT } from "../i18n/LanguageProvider.jsx";

// Provider names are proper nouns (D-13): they stay Latin and never go through t().
const PROVIDERS = [
  { value: "anthropic", label: "Anthropic" },
  { value: "openai", label: "OpenAI" },
  { value: "ollama", label: "Ollama" }
];

// LLM model region — LLM provider/model/API-key setup over the data-service gateway.
// Phase 811 fills the shell (Phase 810) with provider selection, encrypted key
// management, and connection testing. Phase 1308 (D-21) names the region "LLM model"
// and runs every label through the i18n layer; the API key handling is untouched. Errors are kept as objects and described at render so
// the text follows a live language switch.
export default function AiEngineScreen({ active, onBack, project }) {
  const { t, tp } = useT();
  const [provider, setProvider] = React.useState("");
  const [model, setModel] = React.useState("");
  const [apiKey, setApiKey] = React.useState("");
  const [baseUrl, setBaseUrl] = React.useState("");
  const [keyConfigured, setKeyConfigured] = React.useState(false);

  const [models, setModels] = React.useState([]);
  const [modelsLoading, setModelsLoading] = React.useState(false);

  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState(null);

  const [saving, setSaving] = React.useState(false);
  const [saveMsg, setSaveMsg] = React.useState(""); // "" | "saved" | "error"
  const [saveError, setSaveError] = React.useState(null);

  const [testing, setTesting] = React.useState(false);
  const [testResult, setTestResult] = React.useState(null);

  // ── Load settings when screen becomes active ──
  React.useEffect(() => {
    if (!active) return;
    setLoading(true);
    setLoadError(null);
    setTestResult(null);
    getSettings()
      .then((s) => {
        setProvider(s.provider || "");
        setModel(s.model || "");
        setKeyConfigured(s.apiKeyConfigured || false);
        setBaseUrl(s.baseUrl || "");
      })
      .catch((err) => setLoadError(err || new Error("")))
      .finally(() => setLoading(false));
  }, [active]);

  // ── Fetch models when provider changes ──
  React.useEffect(() => {
    if (!provider) {
      setModels([]);
      return;
    }
    setModelsLoading(true);
    fetchModels(provider)
      .then((list) => setModels(Array.isArray(list) ? list : []))
      .catch(() => setModels([]))
      .finally(() => setModelsLoading(false));
  }, [provider]);

  // ── Build model options including the current (saved) model if not in live list ──
  const modelOptions = React.useMemo(() => {
    const fetched = models.map((m) => ({ value: m, label: m }));
    if (model && !models.includes(model)) {
      fetched.unshift({ value: model, label: t("{model} (saved)", { model }) });
    }
    return fetched;
  }, [models, model, t]);

  // ── Save settings ──
  const handleSave = async () => {
    setSaving(true);
    setSaveMsg("");
    setSaveError(null);
    try {
      const payload = {};
      if (provider) payload.provider = provider;
      if (model) payload.model = model;
      if (apiKey.trim()) payload.apiKey = apiKey.trim();
      if (baseUrl.trim()) payload.baseUrl = baseUrl.trim();

      const result = await saveSettings(payload);
      setKeyConfigured(result.apiKeyConfigured || false);
      if (apiKey.trim()) setApiKey(""); // clear after save
      setSaveMsg("saved");
    } catch (err) {
      setSaveMsg("error");
      setSaveError(err || new Error(""));
    } finally {
      setSaving(false);
    }
  };

  // ── Test connection ──
  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const selection = {};
      if (provider) selection.provider = provider;
      if (model) selection.model = model;
      if (apiKey.trim()) selection.apiKey = apiKey.trim();
      if (baseUrl.trim()) selection.baseUrl = baseUrl.trim();
      const result = await testConnection(selection);
      setTestResult(result);
    } catch (err) {
      // `failure` keeps the thrown error; a server-reported `error` string (data) is shown as received.
      setTestResult({ success: false, failure: err || new Error("") });
    } finally {
      setTesting(false);
    }
  };

  // ── Retry load ──
  const handleRetry = () => {
    setLoading(true);
    setLoadError(null);
    getSettings()
      .then((s) => {
        setProvider(s.provider || "");
        setModel(s.model || "");
        setKeyConfigured(s.apiKeyConfigured || false);
        setBaseUrl(s.baseUrl || "");
      })
      .catch((err) => setLoadError(err || new Error("")))
      .finally(() => setLoading(false));
  };

  const testErrorText = testResult?.failure
    ? describeError(testResult.failure, t("Connection test failed"))
    : testResult?.error;

  // ── Render ──
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "var(--surface-canvas)",
        overflow: "auto"
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "28px 40px 60px",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          gap: 28
        }}
      >
        {/* ── Header ── */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            ← {t("Back")}
          </Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
              {t("Region · LLM model")}
            </div>
            <div style={{ font: "400 30px/1.1 var(--font-display)", letterSpacing: "var(--tracking-screen-title)", textTransform: "uppercase" }}>
              {t("LLM model")}
            </div>
          </div>
        </div>

        {/* ── Loading state ── */}
        {loading && (
          <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)" }}>
            <div style={{ font: "400 14px/1.5 var(--font-sans)", color: "var(--text-muted)" }}>
              {t("Loading settings…")}
            </div>
          </div>
        )}

        {/* ── Load error state ── */}
        {loadError && (
          <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)" }}>
            <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>
              {t("Settings unavailable · {reason}", { reason: describeError(loadError, t("Failed to load settings")) })}{" "}
              <span onClick={handleRetry} style={{ cursor: "pointer", textDecoration: "underline" }}>
                {t("Retry")}
              </span>
            </div>
          </div>
        )}

        {/* ── Configuration Card ── */}
        {!loading && !loadError && (
          <>
            <div
              className="dg-frost"
              style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)" }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
                  {t("Configuration")}
                </div>

                {/* Provider */}
                <Select
                  label={t("Provider")}
                  options={PROVIDERS}
                  value={provider}
                  onChange={(e) => {
                    setProvider(e.target.value);
                    setModel("");
                  }}
                />

                {/* Model */}
                <div>
                  <Select
                    label={t("Model")}
                    options={
                      modelOptions.length > 0
                        ? modelOptions
                        : [{ value: "", label: t("Select a provider first") }]
                    }
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    disabled={!provider}
                  />
                  {modelsLoading && (
                    <div
                      style={{
                        font: "400 12px/1.33 var(--font-sans)",
                        color: "var(--text-muted)",
                        marginTop: 6
                      }}
                    >
                      {t("Loading models…")}
                    </div>
                  )}
                  {!modelsLoading && provider && models.length === 0 && (
                    <div
                      style={{
                        font: "400 12px/1.33 var(--font-sans)",
                        color: "var(--text-muted)",
                        marginTop: 6
                      }}
                    >
                      {t("No models discovered — they will populate after a successful connection test")}
                    </div>
                  )}
                </div>

                {/* API Key + Save */}
                <div>
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
                    <div style={{ flex: 1 }}>
                      <Input
                        label={t("API Key")}
                        type="password"
                        placeholder={
                          keyConfigured
                            ? t("Leave blank to keep current key")
                            : t("Enter API key")
                        }
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                      />
                    </div>
                    <Button
                      onClick={handleSave}
                      disabled={saving}
                      style={{ marginBottom: 0, flexShrink: 0 }}
                    >
                      {saving ? t("Saving…") : t("Save")}
                    </Button>
                  </div>

                  {/* Key status + save feedback */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      marginTop: 10
                    }}
                  >
                    {keyConfigured ? (
                      <Badge variant="soft">{t("Key configured")}</Badge>
                    ) : (
                      <Badge variant="outline">{t("No key")}</Badge>
                    )}

                    {saveMsg === "saved" && (
                      <span
                        style={{
                          font: "400 12px/1.33 var(--font-sans)",
                          color: "var(--color-signal-ink, #2d7a4b)"
                        }}
                      >
                        {t("Saved")}
                      </span>
                    )}
                    {saveMsg === "error" && (
                      <span
                        style={{
                          font: "400 12px/1.33 var(--font-sans)",
                          color: "var(--color-signal)"
                        }}
                      >
                        {describeError(saveError, t("Failed to save settings"))}
                      </span>
                    )}
                  </div>
                </div>

                {/* Base URL (optional) */}
                <Input
                  label={t("Base URL")}
                  hint={t("Optional — for OpenAI-compatible providers using a custom endpoint")}
                  placeholder={
                    provider === "openai"
                      ? "https://api.openai.com/v1"
                      : provider === "ollama"
                        ? "http://ollama:11434"
                        : provider === "anthropic"
                          ? "https://api.anthropic.com/v1"
                          : t("Custom API base URL")
                  }
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                />
              </div>
            </div>

            {/* ── Active Configuration Summary ── */}
            <div
              className="dg-frost"
              style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)" }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
                  {t("Active Configuration")}
                </div>
                <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
                  <div>
                    <span
                      style={{
                        font: "400 12px/1.5 var(--font-sans)",
                        color: "var(--text-muted)",
                        display: "block"
                      }}
                    >
                      {t("Provider")}
                    </span>
                    <span
                      style={{
                        font: "500 14px/1.4 var(--font-sans)",
                        color: "var(--color-ink)"
                      }}
                    >
                      {provider || "—"}
                    </span>
                  </div>
                  <div>
                    <span
                      style={{
                        font: "400 12px/1.5 var(--font-sans)",
                        color: "var(--text-muted)",
                        display: "block"
                      }}
                    >
                      {t("Model")}
                    </span>
                    <span
                      style={{
                        font: "500 14px/1.4 var(--font-sans)",
                        color: "var(--color-ink)"
                      }}
                    >
                      {model || "—"}
                    </span>
                  </div>
                  <div>
                    <span
                      style={{
                        font: "400 12px/1.5 var(--font-sans)",
                        color: "var(--text-muted)",
                        display: "block"
                      }}
                    >
                      {t("API Key")}
                    </span>
                    <span
                      style={{
                        font: "500 14px/1.4 var(--font-sans)",
                        color: "var(--color-ink)"
                      }}
                    >
                      {keyConfigured ? (
                        <Badge variant="soft">{t("Configured")}</Badge>
                      ) : (
                        <Badge variant="outline">{t("Not configured")}</Badge>
                      )}
                    </span>
                  </div>
                  {baseUrl && (
                    <div>
                      <span
                        style={{
                          font: "400 12px/1.5 var(--font-sans)",
                          color: "var(--text-muted)",
                          display: "block"
                        }}
                      >
                        {t("Base URL")}
                      </span>
                      <span
                        style={{
                          font: "500 14px/1.4 var(--font-sans)",
                          color: "var(--color-ink)"
                        }}
                      >
                        {baseUrl}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ── Connection Test ── */}
            <div
              className="dg-frost"
              style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)" }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
                  {t("Connection Test")}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <Button
                    variant="secondary"
                    onClick={handleTest}
                    disabled={testing || (!keyConfigured && !apiKey.trim())}
                  >
                    {testing ? t("Testing…") : t("Test Connection")}
                  </Button>
                  {!keyConfigured && (
                    <span
                      style={{
                        font: "400 12px/1.33 var(--font-sans)",
                        color: "var(--text-muted)"
                      }}
                    >
                      {t("Save an API key first")}
                    </span>
                  )}
                </div>
                {testResult && (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                      padding: 14,
                      borderRadius: "var(--radius-inputs)",
                      background: testResult.success
                        ? "var(--color-signal-soft, rgba(45, 122, 75, 0.08))"
                        : "rgba(218, 61, 61, 0.08)",
                      border: `1px solid ${
                        testResult.success
                          ? "var(--color-signal-mid, rgba(45, 122, 75, 0.2))"
                          : "rgba(218, 61, 61, 0.2)"
                      }`
                    }}
                  >
                    <div
                      style={{
                        font: "500 14px/1.4 var(--font-sans)",
                        color: testResult.success
                          ? "var(--color-signal-ink, #2d7a4b)"
                          : "var(--color-signal)"
                      }}
                    >
                      {testResult.success ? t("Connected") : t("Failed")}
                    </div>
                    {testResult.success && (
                      <div
                        style={{
                          font: "400 13px/1.4 var(--font-sans)",
                          color: "var(--text-muted)"
                        }}
                      >
                        {t("Latency: {ms} ms", { ms: Math.round(testResult.latencyMs) })}
                        {testResult.models?.length > 0 &&
                          ` · ${tp("{n} model available", testResult.models.length)}`}
                      </div>
                    )}
                    {!testResult.success && testErrorText && (
                      <div
                        style={{
                          font: "400 13px/1.4 var(--font-sans)",
                          color: "var(--color-signal)",
                          whiteSpace: "pre-wrap"
                        }}
                      >
                        {testErrorText}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
