import { AnimatePresence, motion } from "framer-motion";
import { Bot, Send, Sparkles, UserRound } from "lucide-react";
import { useState } from "react";
import { parseChatCommand } from "../api/client";
import { Button } from "./ui/button";
import { Textarea } from "./ui/input";

const starters = [
  "Autopilot: decide what to scrape.",
  "Scrape all products from this page.",
  "Extract name, price, image, and link.",
  "Only get discounted items."
];

export function AiChatSidebar({ url, availableFields, onCommand, busy }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "I can analyze a URL, scrape selected fields, save templates, and export the latest result."
    }
  ]);
  const [command, setCommand] = useState("");

  async function submitCommand(value = command) {
    const nextCommand = value.trim();
    if (!nextCommand || busy) return;
    setMessages((items) => [...items, { role: "user", content: nextCommand }]);
    setCommand("");
    try {
      const parsed = await parseChatCommand({
        command: nextCommand,
        current_url: /^https?:\/\//i.test(url || "") ? url : null,
        available_fields: availableFields
      });
      setMessages((items) => [...items, { role: "assistant", content: parsed.message }]);
      onCommand(parsed, nextCommand);
    } catch (error) {
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          content: error?.response?.data?.detail || "I could not reach the command parser."
        }
      ]);
    }
  }

  return (
    <aside className="flex h-full flex-col">
      <div className="border-b border-border px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-md border border-sky-300/25 bg-sky-400/12 text-sky-200">
            <Bot size={20} />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">AI command sidebar</p>
            <p className="text-xs text-slate-400">Natural language to scraping actions</p>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-auto px-5 py-5">
        <AnimatePresence initial={false}>
          {messages.map((message, index) => {
            const assistant = message.role === "assistant";
            const Icon = assistant ? Sparkles : UserRound;
            return (
              <motion.div
                key={`${message.content}-${index}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`flex gap-3 ${assistant ? "" : "justify-end"}`}
              >
                {assistant ? (
                  <div className="mt-1 grid h-7 w-7 flex-none place-items-center rounded-md bg-sky-400/12 text-sky-200">
                    <Icon size={15} />
                  </div>
                ) : null}
                <div
                  className={`max-w-[17rem] rounded-panel border px-3 py-2 text-sm leading-6 ${
                    assistant
                      ? "border-border bg-slate-900/80 text-slate-200"
                      : "border-sky-300/25 bg-sky-400/12 text-sky-50"
                  }`}
                >
                  {message.content}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <div className="space-y-3 border-t border-border p-5">
        <div className="flex flex-wrap gap-2">
          {starters.map((starter) => (
            <button
              key={starter}
              onClick={() => submitCommand(starter)}
              className="rounded-md border border-border bg-white/5 px-2.5 py-1.5 text-left text-xs text-slate-300 transition hover:bg-white/10"
            >
              {starter}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <Textarea
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                submitCommand();
              }
            }}
            placeholder="Type a scraping command..."
            className="min-h-16"
          />
          <Button size="icon" disabled={busy} onClick={() => submitCommand()} title="Send command">
            <Send size={17} />
          </Button>
        </div>
      </div>
    </aside>
  );
}
