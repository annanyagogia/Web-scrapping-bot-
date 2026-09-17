import { motion } from "framer-motion";
import { Bot, Database, Download, Loader2, Play, Save, Sparkles } from "lucide-react";
import { ManualSelectorMode } from "../components/ManualSelectorMode";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { FieldPicker } from "../components/FieldPicker";

export function ScrapingWorkspace({
  url,
  analysis,
  selectedFields,
  setSelectedFields,
  customField,
  setCustomField,
  onAddCustomField,
  onScrape,
  onAgentRun,
  onSaveTemplate,
  onExport,
  busy,
  scrapeResult,
  selectors,
  setSelectors,
  error,
  agentDecision
}) {
  const suggested = Array.from(new Set([...(analysis?.suggested_fields || []), ...selectedFields]));
  const hasResult = scrapeResult?.data?.length > 0;

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-sky-200">Scraping Workspace</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Prepare and run selected-field extraction</h1>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot size={17} className="text-sky-300" />
              Current target
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md border border-border bg-slate-950/35 p-3">
              <p className="truncate text-sm text-slate-100">{url || "No URL selected"}</p>
              <p className="mt-1 text-xs text-slate-500">{analysis?.page_title || "Analyze a URL to load page context"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge>{analysis?.website_type || "unknown"}</Badge>
              <Badge tone={analysis?.confidence_score >= 0.7 ? "success" : "warning"}>
                {analysis ? `${Math.round((analysis.confidence_score || 0) * 100)}% confidence` : "not analyzed"}
              </Badge>
              {analysis?.possible_scraping_strategy ? <Badge tone="muted">{analysis.possible_scraping_strategy}</Badge> : null}
              {(analysis?.compliance_reasons || []).map((reason) => (
                <Badge key={reason} tone="danger">
                  {reason}
                </Badge>
              ))}
            </div>
            {analysis?.clarifying_question ? (
              <p className="rounded-md border border-amber-300/25 bg-amber-300/10 p-3 text-sm leading-6 text-amber-100">
                {analysis.clarifying_question}
              </p>
            ) : null}
            {analysis?.compliance_warning ? (
              <p className="rounded-md border border-rose-300/25 bg-rose-300/10 p-3 text-sm leading-6 text-rose-100">
                {analysis.compliance_warning}
              </p>
            ) : null}
            {agentDecision ? (
              <p className="rounded-md border border-sky-300/20 bg-sky-400/10 p-3 text-sm leading-6 text-sky-100">
                {agentDecision.message}
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database size={17} className="text-sky-300" />
              Fields
            </CardTitle>
          </CardHeader>
          <CardContent>
            <FieldPicker
              fields={suggested}
              selected={selectedFields}
              onChange={setSelectedFields}
              customField={customField}
              onCustomFieldChange={setCustomField}
              onAddCustomField={onAddCustomField}
            />
          </CardContent>
        </Card>
      </section>

      <ManualSelectorMode
        selectors={selectors}
        onChange={setSelectors}
        selectedFields={selectedFields}
        onApply={() => onScrape({ manualSelectors: selectors })}
      />

      {error ? <div className="rounded-md border border-rose-400/25 bg-rose-400/10 p-3 text-sm text-rose-100">{error}</div> : null}

      <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap gap-3">
        <Button disabled={busy || !url || !selectedFields.length} onClick={() => onScrape({})}>
          {busy ? <Loader2 size={17} className="animate-spin" /> : <Play size={17} />}
          Run scrape
        </Button>
        <Button variant="secondary" disabled={busy || !url} onClick={() => onAgentRun({ approvedFields: selectedFields })}>
          <Sparkles size={17} />
          Autopilot
        </Button>
        <Button variant="secondary" disabled={!analysis || !selectedFields.length} onClick={onSaveTemplate}>
          <Save size={17} />
          Save template
        </Button>
        <Button variant="secondary" disabled={!hasResult} onClick={() => onExport("csv")}>
          <Download size={17} />
          CSV
        </Button>
        <Button variant="secondary" disabled={!hasResult} onClick={() => onExport("excel")}>
          <Download size={17} />
          Excel
        </Button>
        <Button variant="secondary" disabled={!hasResult} onClick={() => onExport("json")}>
          <Download size={17} />
          JSON
        </Button>
      </motion.section>

      {scrapeResult ? (
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-white">{scrapeResult.total_records} records extracted</p>
              <p className="text-xs text-slate-400">Task #{scrapeResult.task_id || "pending"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={scrapeResult.status === "success" ? "success" : "warning"}>{scrapeResult.status}</Badge>
              {scrapeResult.reused_template ? <Badge tone="success">template reused</Badge> : null}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
