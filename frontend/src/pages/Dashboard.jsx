import { Database, Globe2, History, ListChecks, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchHistory, fetchLiveHistory, fetchTemplates } from "../api/client";
import { DashboardStat } from "../components/DashboardStat";
import { StatusPill } from "../components/StatusPill";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatDate } from "../lib/utils";

export function Dashboard({ refreshKey }) {
  const [history, setHistory] = useState([]);
  const [liveHistory, setLiveHistory] = useState([]);
  const [templates, setTemplates] = useState([]);

  useEffect(() => {
    Promise.all([fetchHistory().catch(() => []), fetchLiveHistory().catch(() => []), fetchTemplates().catch(() => [])]).then(([historyData, liveData, templateData]) => {
      setHistory(historyData);
      setLiveHistory(liveData);
      setTemplates(templateData);
    });
  }, [refreshKey]);

  const stats = useMemo(() => {
    const combinedHistory = [...history, ...liveHistory].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    const total = combinedHistory.length;
    const success = combinedHistory.filter((task) => task.status === "success").length;
    const failed = combinedHistory.filter((task) => task.status === "failed").length;
    const recentDomains = combinedHistory.slice(0, 5).map((task) => {
      try {
        return new URL(task.url).hostname.replace("www.", "");
      } catch {
        return task.url;
      }
    });
    const fieldCounts = new Map();
    history.forEach((task) => {
      (task.selected_fields || []).forEach((field) => fieldCounts.set(field, (fieldCounts.get(field) || 0) + 1));
    });
    const mostUsedFields = Array.from(fieldCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([field]) => field);

    return { total, success, failed, recentDomains, mostUsedFields, combinedHistory };
  }, [history, liveHistory]);

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-sky-200">Home Dashboard</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Jason's Web Scraper Bot</h1>
      </section>

      <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
        <DashboardStat label="Total Scrapes" value={stats.total} icon={History} detail="All recorded scraping tasks" />
        <DashboardStat label="Successful Scrapes" value={stats.success} icon={ShieldCheck} detail="Completed with records" />
        <DashboardStat label="Failed Scrapes" value={stats.failed} icon={ListChecks} detail="Blocked, invalid, or unreachable" />
        <DashboardStat label="Saved Templates" value={templates.length} icon={Database} detail="Reusable domain memories" />
      </section>

      <section className="grid gap-4 2xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe2 size={17} className="text-sky-300" />
              Recent Websites
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.combinedHistory.slice(0, 6).map((task) => (
                <div key={task.id} className="flex items-center justify-between gap-3 rounded-md border border-border bg-slate-950/35 px-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-slate-100">{task.url}</p>
                    <p className="text-xs text-slate-500">{formatDate(task.created_at)}</p>
                  </div>
                  <StatusPill status={task.status} />
                </div>
              ))}
              {!stats.combinedHistory.length ? <p className="text-sm text-slate-400">No scraping history yet.</p> : null}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles size={17} className="text-sky-300" />
              Most Used Fields
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {stats.mostUsedFields.map((field) => (
                <span key={field} className="rounded-md border border-sky-400/20 bg-sky-400/10 px-3 py-2 text-sm text-sky-100">
                  {field}
                </span>
              ))}
              {!stats.mostUsedFields.length ? <p className="text-sm text-slate-400">Run a scrape to build field preferences.</p> : null}
            </div>

            <div className="mt-6 space-y-2">
              {stats.recentDomains.map((domain, index) => (
                <div key={`${domain}-${index}`} className="flex items-center justify-between text-sm text-slate-300">
                  <span>{domain}</span>
                  <span className="text-slate-500">recent</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
