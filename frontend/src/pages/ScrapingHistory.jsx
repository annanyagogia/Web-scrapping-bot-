import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchHistory } from "../api/client";
import { StatusPill } from "../components/StatusPill";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatDate } from "../lib/utils";

export function ScrapingHistory({ refreshKey }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  async function loadHistory() {
    setLoading(true);
    try {
      setHistory(await fetchHistory());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, [refreshKey]);

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-sky-200">Scraping History</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Previous tasks and errors</h1>
        </div>
        <Button variant="secondary" onClick={loadHistory} disabled={loading}>
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh
        </Button>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Latest tasks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-md border border-border">
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-950">
                  <tr>
                    <th className="border-b border-border px-3 py-3 text-left text-xs font-medium uppercase text-slate-400">URL</th>
                    <th className="border-b border-border px-3 py-3 text-left text-xs font-medium uppercase text-slate-400">Type</th>
                    <th className="border-b border-border px-3 py-3 text-left text-xs font-medium uppercase text-slate-400">Records</th>
                    <th className="border-b border-border px-3 py-3 text-left text-xs font-medium uppercase text-slate-400">Status</th>
                    <th className="border-b border-border px-3 py-3 text-left text-xs font-medium uppercase text-slate-400">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((task) => (
                    <tr key={task.id} className="border-b border-border/70 hover:bg-white/5">
                      <td className="max-w-[28rem] px-3 py-3">
                        <p className="truncate text-slate-100">{task.url}</p>
                        {task.error_message ? <p className="mt-1 text-xs text-rose-200">{task.error_message}</p> : null}
                        {task.compliance_warning ? <p className="mt-1 text-xs text-amber-100">{task.compliance_warning}</p> : null}
                      </td>
                      <td className="px-3 py-3 text-slate-300">{task.website_type || "unknown"}</td>
                      <td className="px-3 py-3 text-slate-300">{task.total_records}</td>
                      <td className="px-3 py-3"><StatusPill status={task.status} /></td>
                      <td className="px-3 py-3 text-slate-400">{formatDate(task.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!history.length ? <div className="p-8 text-center text-sm text-slate-400">No history yet.</div> : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
