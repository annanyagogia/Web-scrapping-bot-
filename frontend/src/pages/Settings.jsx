import { Bell, Bot, CalendarClock, Chrome, KeyRound, Mail, MessageCircle, ShieldCheck, Users } from "lucide-react";
import { API_BASE_URL } from "../api/client";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

const addOns = [
  { label: "Scheduled scraping", icon: CalendarClock },
  { label: "Price monitoring", icon: Bell },
  { label: "Deal tracking", icon: ShieldCheck },
  { label: "Email alerts", icon: Mail },
  { label: "Telegram/WhatsApp alerts", icon: MessageCircle },
  { label: "Chrome extension", icon: Chrome },
  { label: "Admin dashboard", icon: Bot },
  { label: "Multi-user accounts", icon: Users },
  { label: "Brand-wise templates", icon: KeyRound },
  { label: "API-based scraping", icon: KeyRound }
];

export function Settings() {
  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-sky-200">Settings</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Runtime and architecture placeholders</h1>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Environment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-slate-950/35 p-3">
              <span className="text-slate-400">API base URL</span>
              <span className="truncate text-slate-100">{API_BASE_URL}</span>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-slate-950/35 p-3">
              <span className="text-slate-400">LLM planner</span>
              <Badge>OpenAI key optional</Badge>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-slate-950/35 p-3">
              <span className="text-slate-400">Database</span>
              <Badge tone="success">SQLite prototype</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Compliance posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-slate-300">
            <p>Only publicly visible data is allowed.</p>
            <p>robots.txt is checked before analysis and scraping.</p>
            <p>CAPTCHA, login, checkout, paywall, rate-limit, and anti-bot bypassing are blocked.</p>
            <p>Video pages are metadata-only.</p>
            <p>For restricted sources, use official APIs or authorized manual data.</p>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Future add-ons</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {addOns.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="flex items-center gap-3 rounded-md border border-border bg-slate-950/35 p-3">
                  <div className="grid h-9 w-9 place-items-center rounded-md bg-sky-400/10 text-sky-200">
                    <Icon size={16} />
                  </div>
                  <span className="text-sm text-slate-200">{item.label}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
