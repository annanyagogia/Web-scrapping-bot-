Web Scraper Bot

Web Scraper Bot is a complete prototype for an AI-guided public web scraping assistant. The app analyzes a URL first, checks basic compliance constraints, suggests scrapeable fields, asks clarifying questions when confidence is low, scrapes only selected fields, previews results in a table, exports CSV/Excel/JSON, and saves reusable templates for future runs. It also includes a Live Web Scraper that opens webpages with Playwright, waits for JavaScript-rendered content, captures screenshots, extracts visible tables/products/links/images/filters, exports the result, and saves live scrape history.

## Stack

- Frontend: React, Vite, Tailwind CSS, shadcn-style components, Framer Motion, Axios, TanStack Table
- Backend: FastAPI, BeautifulSoup, Requests, Playwright, Pandas, SQLite, SQLAlchemy, Pydantic
- AI planner: OpenAI-compatible optional integration with heuristic fallback
- Database: SQLite prototype database

## Project Structure

```text
jasons-web-scraper-bot/
├── backend/
│   ├── main.py
│   ├── live_page_scraper.py
│   ├── ai_structurer.py
│   ├── exporters.py
│   ├── scrape_history.py
│   ├── scrape_templates.py
│   ├── requirements.txt
│   ├── routes/
│   ├── services/
│   ├── database/
│   │   └── scraper.db
│   ├── static/
│   │   ├── screenshots/
│   │   └── downloads/
│   ├── utils/
│   └── exports/
├── frontend/
│   ├── package.json
│   └── src/
├── .env.example
└── README.md
```

## Installation

```bash
cd jasons-web-scraper-bot
cp .env.example .env
```

Edit `.env` if needed. `OPENAI_API_KEY` is optional; without it, the backend uses deterministic page-analysis heuristics.

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

The SQLite database is created automatically on startup from `DATABASE_URL`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Environment Variables

```bash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./scraper_bot.db
PLAYWRIGHT_HEADLESS=true
MAX_SCRAPE_RECORDS=500
REQUEST_TIMEOUT=30
USER_AGENT=JasonWebScraperBot/1.0
VITE_API_BASE_URL=http://localhost:8000
```

## Example Scraping Flow

1. Open the dashboard.
2. Go to URL Analyzer and enter a public website URL.
3. Click Analyze for manual review or Autopilot for agent-led scraping.
4. The backend validates the URL, checks robots.txt, loads static HTML, and falls back to Playwright for JavaScript-rendered pages.
5. In Autopilot mode, the agent scrapes recommended fields automatically when confidence is high enough.
6. If confidence is low, fields are ambiguous, or the page contains a special case such as embedded video, the agent asks a clarifying question before scraping.
7. The analyzer extracts title, headings, links, images, tables, product-card signals, metadata, Open Graph data, and schema.org JSON-LD.
8. The AI planner classifies the site type and suggests fields.
9. Select or approve fields such as `product_name`, `price`, `image_url`, and `product_url`.
10. Preview results in the Results Table.
11. Export CSV, Excel, or JSON.
12. Save a template so the same domain can reuse successful selectors first next time.

## Live Web Scraper Flow

1. Go to Live Scraper.
2. Enter a public URL.
3. Choose Auto Detect or force Product Listings, Tables, Text Content, Links, Images, Filters, or Custom Instruction.
4. Choose JSON, CSV, Excel, Markdown, or Plain Text.
5. Leave Scrape full page enabled when the page lazy-loads products or cards.
6. Click Start Scraping.
7. The backend opens the page with Playwright, waits for rendered content, optionally scrolls, captures visible text/HTML/links/images/buttons/forms, saves a screenshot, detects page type, extracts useful data, structures rows, exports a file, saves history, and stores a reusable domain template when confidence is high.
8. The UI displays the structured table, JSON preview, Markdown table, screenshot preview, download link, confidence score, and scrape explanation.

Screenshots are saved in `backend/static/screenshots/`. Live scrape downloads are saved in `backend/static/downloads/`. Live history/templates are stored in `backend/database/scraper.db`.

## API Endpoints

- `POST /api/analyze-url`
- `POST /api/agent-run`
- `POST /api/scrape`
- `POST /api/save-template`
- `GET /api/templates`
- `GET /api/history`
- `GET /api/export/{task_id}?format=csv`
- `POST /api/chat-command`
- `POST /api/live-scrape`
- `GET /api/scrape-history`
- `GET /api/download/{file_name}`
- `POST /api/save-scrape-template`
- `GET /api/scrape-template/{domain}`

### Live Scrape Request

```json
{
  "url": "https://example.com/products",
  "mode": "auto",
  "instruction": "extract product listings",
  "output_format": "json",
  "scrape_full_page": true
}
```

### Live Scrape Response Highlights

- `page_type`: detected structure such as `product_listing`, `table_page`, `directory_or_link_page`, or `article_or_content_page`
- `data`: structured rows
- `columns`: display/export columns
- `download_url`: file in `static/downloads`
- `screenshot_url`: rendered screenshot in `static/screenshots`
- `scrape_explanation`: source, method, records found, confidence, issues, and extraction notes

## Compliance Warning

This prototype is designed for publicly visible data only. It checks robots.txt, blocks sensitive URL paths, warns on websites that commonly restrict automation, and stops when CAPTCHA, access denial, bot protection, login-only, payment, paywall, rate-limit, or similar protected flows are detected. It does not bypass authentication, paywalls, CAPTCHA, anti-bot protection, or website access controls. For restricted sources, use an official API or authorized source data. Video pages are metadata-only; the app does not download videos.

## Known Limitations

- Selector inference is heuristic and will not handle every website layout.
- robots.txt checks are basic and do not replace legal review of a website's terms.
- Playwright requires browser installation and may fail on sites with strict bot protection.
- The AI planner uses OpenAI only when an API key is configured; otherwise it uses local heuristics.
- The manual selector mode accepts CSS selectors in this prototype rather than a true browser click overlay.
- SQLite is suitable for local prototyping, not high-volume production scraping.

## Future Upgrades

Architecture placeholders are included for:

- Scheduled scraping
- Price monitoring
- Deal tracking
- Email alerts
- Telegram/WhatsApp alerts
- Chrome extension
- Admin dashboard
- Multi-user accounts
- Brand-wise scraper templates
- API-based scraping where available

Production upgrades should add queue workers, per-domain rate limits, user accounts, encrypted secrets, audit logs, stronger terms-of-service review flows, browser session isolation, and API-first integrations for websites that provide official data access.
