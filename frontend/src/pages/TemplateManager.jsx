import { Database, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchTemplates } from "../api/client";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatDate } from "../lib/utils";

export function TemplateManager({ refreshKey, onSaveTemplate, selectedFields, analysis }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);

  async function loadTemplates() {
    setLoading(true);
    try {
      setTemplates(await fetchTemplates());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTemplates();
  }, [refreshKey]);

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-sky-200">Template Manager</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Self-learning scraping templates</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={loadTemplates} disabled={loading}>
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </Button>
          <Button disabled={!selectedFields.length || !analysis} onClick={onSaveTemplate}>
            <Save size={16} />
            Save current
          </Button>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        {templates.map((template) => (
          <Card key={template.id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database size={17} className="text-sky-300" />
                {template.template_name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge>{template.website_domain}</Badge>
                <Badge tone="muted">{template.website_type}</Badge>
                <Badge tone="success">{template.preferred_fields?.length || 0} fields</Badge>
              </div>
              <div className="flex flex-wrap gap-2">
                {(template.preferred_fields || []).map((field) => (
                  <span key={field} className="rounded-md border border-border bg-slate-950/35 px-2.5 py-1.5 text-xs text-slate-300">
                    {field}
                  </span>
                ))}
              </div>
              <div className="rounded-md border border-border bg-slate-950/35 p-3 text-xs text-slate-400">
                Updated {formatDate(template.updated_at)}
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      {!templates.length ? <Card><CardContent className="text-sm text-slate-400">No templates saved yet.</CardContent></Card> : null}
    </div>
  );
}
