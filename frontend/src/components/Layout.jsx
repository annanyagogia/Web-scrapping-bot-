import {
  Bot,
  Clock3,
  Database,
  Download,
  Gauge,
  Globe2,
  History,
  LayoutDashboard,
  Link2,
  Settings,
  Sparkles
} from "lucide-react";
import { cn } from "../lib/utils";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "live", label: "Live Scraper", icon: Globe2 },
  { id: "analyzer", label: "URL Analyzer", icon: Link2 },
  { id: "workspace", label: "Workspace", icon: Bot },
  { id: "results", label: "Results", icon: Download },
  { id: "templates", label: "Templates", icon: Database },
  { id: "history", label: "History", icon: History },
  { id: "settings", label: "Settings", icon: Settings }
];

export function Layout({ activePage, onNavigate, children, sidebar }) {
  return (
    <div className="min-h-screen text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-border bg-slate-950/78 px-4 py-5 backdrop-blur-xl lg:block">
        <div className="mb-7 flex items-center gap-3 px-2">
          <div className="grid h-11 w-11 place-items-center rounded-md border border-sky-300/25 bg-sky-400/12 text-sky-200">
            <Sparkles size={21} />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Jason's Web Scraper Bot</p>
            <p className="text-xs text-slate-400">AI scraping assistant</p>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={cn(
                  "flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm transition",
                  active ? "bg-sky-400/14 text-sky-100" : "text-slate-400 hover:bg-white/7 hover:text-slate-100"
                )}
              >
                <Icon size={17} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="absolute bottom-5 left-4 right-4 rounded-panel border border-sky-400/18 bg-sky-400/8 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm text-sky-100">
            <Gauge size={16} />
            Compliance guard
          </div>
          <p className="text-xs leading-5 text-slate-400">
            Public data only, robots.txt checks, no CAPTCHA or paywall bypassing.
          </p>
        </div>
      </aside>

      <div className="lg:pl-72 xl:pr-[25rem]">
        <header className="sticky top-0 z-20 border-b border-border bg-slate-950/68 px-4 py-3 backdrop-blur-xl lg:px-7">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white lg:hidden">Jason's Web Scraper Bot</p>
              <p className="text-xs text-slate-400">Analyze first. Ask when unclear. Scrape selected public data.</p>
            </div>
            <div className="flex items-center gap-3 rounded-md border border-border bg-slate-950/55 px-3 py-2 text-xs text-slate-300">
              <span className="status-dot" />
              <Clock3 size={14} />
              Live prototype
            </div>
          </div>
        </header>

        <main className="px-4 py-6 lg:px-7">{children}</main>
      </div>

      <div className="fixed bottom-0 right-0 top-0 z-40 hidden w-[25rem] border-l border-border bg-slate-950/80 backdrop-blur-xl xl:block">
        {sidebar}
      </div>

      <nav className="fixed bottom-0 left-0 right-0 z-50 grid grid-cols-8 border-t border-border bg-slate-950/90 px-2 py-2 backdrop-blur-xl lg:hidden">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={cn("grid place-items-center gap-1 rounded-md py-2 text-[10px]", active ? "text-sky-200" : "text-slate-500")}
            >
              <Icon size={17} />
              {item.label.split(" ")[0]}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
