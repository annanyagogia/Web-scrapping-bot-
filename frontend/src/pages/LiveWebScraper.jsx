import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Download,
  FileJson,
  FileText,
  Filter,
  History,
  Image,
  Link2,
  Loader2,
  Play,
  RefreshCw,
  Sparkles,
  Table2
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { assetUrl, fetchLiveHistory, liveDownloadUrl, liveScrape } from "../api/client";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input, Textarea } from "../components/ui/input";
import { formatDate } from "../lib/utils";

const progressSteps = [
  "Opening live webpage...",
  "Waiting for JavaScript-rendered content...",
  "Reading visible page content...",
  "Detecting page structure...",
  "Extracting useful data...",
  "Formatting output...",
  "Saving scrape history..."
];

const scrapeModes = [
  ["auto", "Auto Detect"],
  ["product_listing", "Product Listings"],
  ["tables", "Tables"],
  ["text_content", "Text Content"],
  ["links", "Links"],
  ["images", "Images"],
  ["filters", "Filters"],
  ["custom", "Custom Instruction"]
];

const outputFormats = [
  ["json", "JSON"],
  ["csv", "CSV"],
  ["excel", "Excel"],
  ["markdown", "Markdown"],
  ["text", "Plain Text"]
];

function confidenceTone(value) {
  if (value >= 0.75) return "success";
  if (value >= 0.5) return "warning";
  return "danger";
}

function cellValue(value) {
  if (Array.isArray(value)) return value.join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}

function modeForClarification(option) {
  const lower = option.toLowerCase();
  if (lower.includes("product")) return "product_listing";
  if (lower.includes("table")) return "tables";
  if (lower.includes("filter")) return "filters";
  if (lower.includes("link")) return "links";
  if (lower.includes("image")) return "images";
  return "custom";
}

export function LiveWebScraper({ url, setUrl, refreshKey, onRefresh }) {
  const [mode, setMode] = useState("auto");
  const [instruction, setInstruction] = useState("extract product listings");
  const [outputFormat, setOutputFormat] = useState("json");
  const [scrapeFullPage, setScrapeFullPage] = useState(true);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const progressIndex = useRef(0);

  const rows = result?.data || [];
  const columns = result?.columns?.length ? result.columns : Array.from(new Set(rows.flatMap((row) => Object.keys(row || {}))));
  const explanation = result?.scrape_explanation || {};
  const confidence = explanation.confidence || 0;

  const prettyJson = useMemo(() => JSON.stringify(rows, null, 2), [rows]);

  async function loadHistory() {
    try {
      setHistory(await fetchLiveHistory());
    } catch {
      setHistory([]);
    }
  }

  useEffect(() => {
    loadHistory();
  }, [refreshKey]);

  async function startLiveScrape(nextMode = mode) {
    if (!url.trim()) {
      setError("Enter a public website URL before starting a live scrape.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    progressIndex.current = 0;
    setStatus(progressSteps[0]);

    const interval = window.setInterval(() => {
      progressIndex.current = Math.min(progressIndex.current + 1, progressSteps.length - 2);
      setStatus(progressSteps[progressIndex.current]);
    }, 1300);

    try {
      const payload = {
        url,
        mode: nextMode,
        instruction,
        output_format: outputFormat,
        scrape_full_page: scrapeFullPage
      };
      const data = await liveScrape(payload);
      setStatus(progressSteps[progressSteps.length - 1]);
      setResult(data);
      if (!data.success) {
        setError(data.message || "Scraping failed.");
      } else {
        onRefresh?.();
      }
      await loadHistory();
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Something went wrong.");
    } finally {
      window.clearInterval(interval);
      setLoading(false);
      window.setTimeout(() => setStatus(""), 500);
    }
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-sky-200">Live Web Scraper</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Inspect rendered pages and extract structured data</h1>
        </div>
        <Badge tone="success" className="w-fit">
          <Sparkles size={14} />
          Playwright live render
        </Badge>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play size={17} className="text-sky-300" />
              Scrape Setup
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase text-slate-400">Website URL</label>
              <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/products" />
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-xs font-medium uppercase text-slate-400">Scrape Mode</label>
                <select
                  value={mode}
                  onChange={(event) => setMode(event.target.value)}
                  className="h-11 w-full rounded-md border border-border bg-slate-950/65 px-3 text-sm text-foreground outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                >
                  {scrapeModes.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium uppercase text-slate-400">Output Format</label>
                <select
                  value={outputFormat}
                  onChange={(event) => setOutputFormat(event.target.value)}
                  className="h-11 w-full rounded-md border border-border bg-slate-950/65 px-3 text-sm text-foreground outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                >
                  {outputFormats.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium uppercase text-slate-400">Custom Instruction</label>
              <Textarea
                value={instruction}
                onChange={(event) => setInstruction(event.target.value)}
                placeholder="Example: extract product name, seller rating, brand, minimum quantity, and visible prices"
              />
            </div>

            <label className="flex items-center justify-between gap-4 rounded-md border border-border bg-slate-950/35 px-3 py-3">
              <span>
                <span className="block text-sm font-medium text-slate-100">Scrape full page</span>
                <span className="text-xs text-slate-500">Scroll before extraction to load lazy content.</span>
              </span>
              <input
                type="checkbox"
                checked={scrapeFullPage}
                onChange={(event) => setScrapeFullPage(event.target.checked)}
                className="h-5 w-5 accent-sky-300"
              />
            </label>

            {status ? (
              <div className="flex items-center gap-3 rounded-md border border-sky-300/20 bg-sky-400/10 px-3 py-3 text-sm text-sky-100">
                <Loader2 size={17} className="animate-spin" />
                {status}
              </div>
            ) : null}

            {error ? (
              <div className="rounded-md border border-rose-400/25 bg-rose-400/10 p-3 text-sm leading-6 text-rose-100">
                {error}
              </div>
            ) : null}

            {result?.needs_clarification ? (
              <div className="rounded-md border border-amber-300/25 bg-amber-300/10 p-3">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-amber-100">
                  <AlertTriangle size={16} />
                  Choose a section
                </div>
                <div className="flex flex-wrap gap-2">
                  {result.clarification_options.map((option) => (
                    <Button
                      key={option}
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        const nextMode = modeForClarification(option);
                        setMode(nextMode);
                        startLiveScrape(nextMode);
                      }}
                    >
                      {option}
                    </Button>
                  ))}
                </div>
              </div>
            ) : null}

            <Button disabled={loading} onClick={() => startLiveScrape()}>
              {loading ? <Loader2 size={17} className="animate-spin" /> : <Play size={17} />}
              Start Scraping
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History size={17} className="text-sky-300" />
              Live History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-3 flex justify-end">
              <Button variant="ghost" size="sm" onClick={loadHistory}>
                <RefreshCw size={15} />
                Refresh
              </Button>
            </div>
            <div className="max-h-[31rem] space-y-3 overflow-auto pr-1">
              {history.map((item) => (
                <div key={item.id} className="rounded-md border border-border bg-slate-950/35 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm text-slate-100">{item.url}</p>
                      <p className="mt-1 text-xs text-slate-500">{formatDate(item.created_at)}</p>
                    </div>
                    <Badge tone={item.status === "success" ? "success" : "danger"}>{item.status}</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <span>{item.records_found} records</span>
                    <span>{Math.round((item.confidence || 0) * 100)}% confidence</span>
                    {item.download_file ? (
                      <a className="text-sky-200 hover:text-sky-100" href={liveDownloadUrl(item.download_file)} target="_blank" rel="noreferrer">
                        Download again
                      </a>
                    ) : null}
                  </div>
                </div>
              ))}
              {!history.length ? <p className="text-sm text-slate-400">No live scrape history yet.</p> : null}
            </div>
          </CardContent>
        </Card>
      </section>

      {result ? (
        <section className="grid gap-4 2xl:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Table2 size={17} className="text-sky-300" />
                  Results
                </CardTitle>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={result.success ? "success" : "danger"}>{result.success ? "scraped" : "needs attention"}</Badge>
                  <Badge tone={confidenceTone(confidence)}>{Math.round(confidence * 100)}% confidence</Badge>
                  {result.template_reused ? <Badge tone="success">template reused</Badge> : null}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-lg font-semibold text-white">{result.page_title || "Untitled page"}</p>
                <p className="mt-1 text-sm leading-6 text-slate-400">{result.summary || result.message}</p>
              </div>

              <div className="flex flex-wrap gap-2">
                {result.download_url ? (
                  <a href={assetUrl(result.download_url)} target="_blank" rel="noreferrer">
                    <Button variant="secondary">
                      <Download size={16} />
                      Download
                    </Button>
                  </a>
                ) : null}
                {result.screenshot_url ? (
                  <a href={assetUrl(result.screenshot_url)} target="_blank" rel="noreferrer">
                    <Button variant="secondary">
                      <Camera size={16} />
                      Screenshot
                    </Button>
                  </a>
                ) : null}
              </div>

              <div className="overflow-hidden rounded-md border border-border">
                <div className="max-h-[32rem] overflow-auto">
                  <table className="min-w-full border-collapse text-sm">
                    <thead className="sticky top-0 bg-slate-950">
                      <tr>
                        {columns.map((column) => (
                          <th key={column} className="border-b border-border px-3 py-3 text-left text-xs font-medium uppercase text-slate-400">
                            {column}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, index) => (
                        <tr key={index} className="border-b border-border/70 hover:bg-white/5">
                          {columns.map((column) => (
                            <td key={column} className="max-w-80 px-3 py-3 align-top text-slate-200">
                              <span className="line-clamp-4 break-words">{cellValue(row[column])}</span>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!rows.length ? <div className="p-8 text-center text-sm text-slate-400">No structured rows were produced.</div> : null}
              </div>

              {result.markdown_table ? (
                <div>
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
                    <FileText size={16} className="text-sky-300" />
                    Markdown Table
                  </div>
                  <pre className="max-h-56 overflow-auto rounded-md border border-border bg-slate-950/60 p-3 text-xs leading-5 text-slate-300">
                    {result.markdown_table}
                  </pre>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 size={17} className="text-emerald-300" />
                  Scrape Explanation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="grid gap-2 sm:grid-cols-2">
                  <Badge tone="muted">{explanation.page_type_detected || result.page_type || "unknown"}</Badge>
                  <Badge tone={confidenceTone(confidence)}>{Math.round(confidence * 100)}% confidence</Badge>
                  <Badge tone="default">{explanation.records_found || 0} records</Badge>
                  <Badge tone={result.pagination?.detected ? "warning" : "success"}>
                    {result.pagination?.detected ? "pagination detected" : "single page"}
                  </Badge>
                </div>
                <p className="leading-6 text-slate-400">{explanation.data_source}</p>
                <p className="leading-6 text-slate-400">{explanation.extraction_method}</p>
                {explanation.extraction_notes?.length ? (
                  <div className="space-y-2">
                    {explanation.extraction_notes.map((note) => (
                      <p key={note} className="rounded-md border border-emerald-300/20 bg-emerald-300/10 p-2 text-emerald-100">
                        {note}
                      </p>
                    ))}
                  </div>
                ) : null}
                {explanation.issues?.length ? (
                  <div className="space-y-2">
                    {explanation.issues.map((issue) => (
                      <p key={issue} className="rounded-md border border-amber-300/20 bg-amber-300/10 p-2 text-amber-100">
                        {issue}
                      </p>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileJson size={17} className="text-sky-300" />
                  JSON Preview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="max-h-80 overflow-auto rounded-md border border-border bg-slate-950/60 p-3 text-xs leading-5 text-slate-300">
                  {prettyJson}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Camera size={17} className="text-sky-300" />
                  Screenshot Preview
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.screenshot_url ? (
                  <img
                    src={assetUrl(result.screenshot_url)}
                    alt="Rendered webpage screenshot"
                    className="max-h-[32rem] w-full rounded-md border border-border object-contain"
                  />
                ) : (
                  <p className="text-sm text-slate-400">No screenshot was captured for this run.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </section>
      ) : null}

      <section className="grid gap-3 md:grid-cols-4">
        <div className="rounded-md border border-border bg-slate-950/35 p-3">
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <Table2 size={16} className="text-sky-300" />
            Tables
          </div>
          <p className="mt-1 text-2xl font-semibold text-white">{result?.raw_counts?.tables || 0}</p>
        </div>
        <div className="rounded-md border border-border bg-slate-950/35 p-3">
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <Link2 size={16} className="text-sky-300" />
            Links
          </div>
          <p className="mt-1 text-2xl font-semibold text-white">{result?.raw_counts?.links || 0}</p>
        </div>
        <div className="rounded-md border border-border bg-slate-950/35 p-3">
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <Image size={16} className="text-sky-300" />
            Images
          </div>
          <p className="mt-1 text-2xl font-semibold text-white">{result?.raw_counts?.images || 0}</p>
        </div>
        <div className="rounded-md border border-border bg-slate-950/35 p-3">
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <Filter size={16} className="text-sky-300" />
            Filters
          </div>
          <p className="mt-1 text-2xl font-semibold text-white">{result?.raw_counts?.filters || 0}</p>
        </div>
      </section>
    </div>
  );
}
