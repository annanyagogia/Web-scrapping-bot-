import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import { agentRun, analyzeUrl, exportUrl, saveTemplate, scrapeUrl } from "../api/client";
import { AiChatSidebar } from "../components/AiChatSidebar";
import { Layout } from "../components/Layout";
import { Dashboard } from "../pages/Dashboard";
import { LiveWebScraper } from "../pages/LiveWebScraper";
import { ResultsTablePage } from "../pages/ResultsTablePage";
import { ScrapingHistory } from "../pages/ScrapingHistory";
import { ScrapingWorkspace } from "../pages/ScrapingWorkspace";
import { Settings } from "../pages/Settings";
import { TemplateManager } from "../pages/TemplateManager";
import { UrlAnalyzer } from "../pages/UrlAnalyzer";

function errorMessage(error) {
  return error?.response?.data?.detail || error?.message || "Something went wrong.";
}

function cleanSelectors(selectors) {
  return Object.fromEntries(Object.entries(selectors || {}).filter(([, value]) => value && value.trim()));
}

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [url, setUrl] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [selectedFields, setSelectedFields] = useState([]);
  const [scrapeResult, setScrapeResult] = useState(null);
  const [selectors, setSelectors] = useState({});
  const [customField, setCustomField] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [agentDecision, setAgentDecision] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const availableFields = useMemo(
    () => Array.from(new Set([...(analysis?.suggested_fields || []), ...selectedFields])),
    [analysis, selectedFields]
  );

  function addCustomField() {
    const field = customField.trim().replace(/\s+/g, "_").toLowerCase();
    if (!field) return;
    setSelectedFields((fields) => Array.from(new Set([...fields, field])));
    setCustomField("");
  }

  async function handleAnalyze() {
    setError("");
    setAgentDecision(null);
    setBusy(true);
    try {
      const data = await analyzeUrl(url);
      setAnalysis(data);
      setSelectedFields(data.suggested_fields?.slice(0, 5) || []);
      setActivePage("analyzer");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleScrape({ manualSelectors, fieldsOverride } = {}) {
    const fields = fieldsOverride?.length ? fieldsOverride : selectedFields;
    if (!fields.length) {
      setError("Please select at least one field before scraping.");
      return;
    }
    setError("");
    setAgentDecision(null);
    setBusy(true);
    try {
      const data = await scrapeUrl({
        url,
        fields,
        format: "json",
        manual_selectors: Object.keys(cleanSelectors(manualSelectors || {})).length ? cleanSelectors(manualSelectors) : null
      });
      setScrapeResult(data);
      setSelectedFields(fields);
      setRefreshKey((key) => key + 1);
      setActivePage("results");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleAgentRun({ instruction = "", approvedFields = [] } = {}) {
    if (!url) {
      setError("Enter a public URL before starting autopilot.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const decision = await agentRun({
        url,
        user_instruction: instruction,
        approved_fields: approvedFields,
        confidence_threshold: 0.7,
        format: "json"
      });
      setAgentDecision(decision);
      setAnalysis(decision.analysis);
      setSelectedFields(decision.selected_fields?.length ? decision.selected_fields : decision.analysis?.suggested_fields?.slice(0, 5) || []);

      if (decision.mode === "scraped" || decision.mode === "empty") {
        setScrapeResult(decision.scrape_result);
        setRefreshKey((key) => key + 1);
        setActivePage(decision.scrape_result?.data?.length ? "results" : "workspace");
        return;
      }

      setError(decision.mode === "blocked" ? decision.message : "");
      setActivePage(decision.mode === "blocked" ? "analyzer" : "workspace");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveTemplate() {
    if (!analysis || !selectedFields.length) return;
    setError("");
    setBusy(true);
    try {
      await saveTemplate({
        template_name: `${analysis.website_type.replaceAll("_", " ")} scraper`,
        website_type: analysis.website_type,
        fields: selectedFields,
        website_url: url,
        last_successful_selectors: cleanSelectors(selectors)
      });
      setRefreshKey((key) => key + 1);
      setActivePage("templates");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function handleExport(format) {
    if (!scrapeResult?.task_id) {
      setError("Run a scrape before exporting.");
      return;
    }
    window.open(exportUrl(scrapeResult.task_id, format), "_blank", "noopener,noreferrer");
  }

  async function handleChatCommand(parsed, rawCommand = "") {
    if (parsed.action === "analyze") {
      await handleAnalyze();
      return;
    }
    if (parsed.action === "agent_run") {
      await handleAgentRun({ instruction: rawCommand, approvedFields: parsed.fields });
      return;
    }
    if (parsed.action === "scrape") {
      const fields = parsed.fields?.length ? parsed.fields : selectedFields;
      if (!fields.length) {
        await handleAgentRun({ instruction: rawCommand });
        return;
      }
      setSelectedFields(fields);
      await handleScrape({ fieldsOverride: fields });
      return;
    }
    if (parsed.action === "export") {
      handleExport(parsed.export_format || "csv");
      return;
    }
    if (parsed.action === "save_template") {
      await handleSaveTemplate();
    }
  }

  const pageProps = {
    url,
    setUrl,
    analysis,
    selectedFields,
    setSelectedFields,
    customField,
    setCustomField,
    onAddCustomField: addCustomField,
    onAnalyze: handleAnalyze,
    onAgentRun: handleAgentRun,
    onScrape: handleScrape,
    onSaveTemplate: handleSaveTemplate,
    onExport: handleExport,
    busy,
    error,
    agentDecision,
    scrapeResult,
    selectors,
    setSelectors,
    refreshKey
  };

  const page = {
    dashboard: <Dashboard refreshKey={refreshKey} />,
    live: <LiveWebScraper url={url} setUrl={setUrl} refreshKey={refreshKey} onRefresh={() => setRefreshKey((key) => key + 1)} />,
    analyzer: <UrlAnalyzer {...pageProps} />,
    workspace: <ScrapingWorkspace {...pageProps} />,
    results: <ResultsTablePage scrapeResult={scrapeResult} onExport={handleExport} />,
    templates: (
      <TemplateManager
        refreshKey={refreshKey}
        onSaveTemplate={handleSaveTemplate}
        selectedFields={selectedFields}
        analysis={analysis}
      />
    ),
    history: <ScrapingHistory refreshKey={refreshKey} />,
    settings: <Settings />
  }[activePage];

  return (
    <Layout
      activePage={activePage}
      onNavigate={setActivePage}
      sidebar={
        <AiChatSidebar
          url={url}
          availableFields={availableFields}
          busy={busy}
          onCommand={handleChatCommand}
        />
      }
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={activePage}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.18 }}
        >
          {page}
        </motion.div>
      </AnimatePresence>
    </Layout>
  );
}
