import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000
});

export async function analyzeUrl(url) {
  const { data } = await api.post("/api/analyze-url", { url });
  return data;
}

export async function scrapeUrl(payload) {
  const { data } = await api.post("/api/scrape", payload);
  return data;
}

export async function liveScrape(payload) {
  const { data } = await api.post("/api/live-scrape", payload);
  return data;
}

export async function agentRun(payload) {
  const { data } = await api.post("/api/agent-run", payload);
  return data;
}

export async function fetchTemplates() {
  const { data } = await api.get("/api/templates");
  return data;
}

export async function saveTemplate(payload) {
  const { data } = await api.post("/api/save-template", payload);
  return data;
}

export async function fetchHistory() {
  const { data } = await api.get("/api/history");
  return data;
}

export async function fetchLiveHistory() {
  const { data } = await api.get("/api/scrape-history");
  return data;
}

export async function parseChatCommand(payload) {
  const { data } = await api.post("/api/chat-command", payload);
  return data;
}

export function exportUrl(taskId, format) {
  return `${API_BASE_URL}/api/export/${taskId}?format=${format}`;
}

export function assetUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE_URL}${path}`;
}

export function liveDownloadUrl(fileName) {
  return `${API_BASE_URL}/api/download/${encodeURIComponent(fileName)}`;
}
