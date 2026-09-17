import { motion } from "framer-motion";
import { AlertTriangle, Bot, ExternalLink, Search, Sparkles } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { FieldPicker } from "../components/FieldPicker";

export function UrlAnalyzer({
  url,
  setUrl,
  analysis,
  selectedFields,
  setSelectedFields,
  customField,
  setCustomField,
  onAddCustomField,
  onAnalyze,
  onAgentRun,
  busy,
  error,
  agentDecision
}) {
  const suggested = Array.from(new Set([...(analysis?.suggested_fields || []), ...selectedFields]));

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-sky-200">URL Analyzer</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Inspect a public page before scraping</h1>
      </section>

      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row">
            <Input
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com/products"
              inputMode="url"
            />
            <Button onClick={onAnalyze} disabled={busy || !url}>
              <Search size={17} />
              Analyze
            </Button>
            <Button variant="secondary" onClick={() => onAgentRun({})} disabled={busy || !url}>
              <Sparkles size={17} />
              Autopilot
            </Button>
          </div>
          {error ? (
            <div className="flex items-start gap-2 rounded-md border border-rose-400/25 bg-rose-400/10 p-3 text-sm text-rose-100">
              <AlertTriangle size={17} className="mt-0.5 flex-none" />
              {error}
            </div>
          ) : null}
          {agentDecision ? (
            <div className="rounded-md border border-sky-300/20 bg-sky-400/10 p-3 text-sm leading-6 text-sky-100">
              <span className="font-medium">{agentDecision.mode.replace("_", " ")}:</span> {agentDecision.message}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {analysis ? (
        <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot size={17} className="text-sky-300" />
                AI-guided plan
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-md border border-border bg-slate-950/35 p-3">
                  <p className="text-xs text-slate-500">Website type</p>
                  <p className="mt-1 text-sm font-medium text-slate-100">{analysis.website_type}</p>
                </div>
                <div className="rounded-md border border-border bg-slate-950/35 p-3">
                  <p className="text-xs text-slate-500">Strategy</p>
                  <p className="mt-1 text-sm font-medium text-slate-100">{analysis.possible_scraping_strategy}</p>
                </div>
                <div className="rounded-md border border-border bg-slate-950/35 p-3">
                  <p className="text-xs text-slate-500">Confidence</p>
                  <p className="mt-1 text-sm font-medium text-slate-100">{Math.round((analysis.confidence_score || 0) * 100)}%</p>
                </div>
              </div>

              {agentDecision?.decision_reason ? (
                <div className="rounded-md border border-border bg-slate-950/35 p-3 text-sm leading-6 text-slate-300">
                  Agent decision: {agentDecision.decision_reason.replaceAll("_", " ")}
                </div>
              ) : null}

              {analysis.clarifying_question ? (
                <div className="rounded-md border border-amber-300/25 bg-amber-300/10 p-3 text-sm leading-6 text-amber-100">
                  {analysis.clarifying_question}
                </div>
              ) : null}

              {analysis.compliance_warning ? (
                <div className="rounded-md border border-sky-300/20 bg-sky-400/10 p-3 text-sm leading-6 text-sky-100">
                  {analysis.compliance_warning}
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                {(analysis.detected_sections || []).map((section) => (
                  <Badge key={section}>{section}</Badge>
                ))}
                {(analysis.compliance_reasons || []).map((reason) => (
                  <Badge key={reason} tone="danger">
                    {reason}
                  </Badge>
                ))}
                {analysis.template_available ? <Badge tone="success">saved template</Badge> : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ExternalLink size={17} className="text-sky-300" />
                Select fields
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
        </motion.section>
      ) : null}
    </div>
  );
}
