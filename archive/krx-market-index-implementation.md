# Archived KRX Market Index Implementation

Archived on: 2026-06-30

Reason: Removed from the active dashboard because the displayed data was not reliably reflecting the latest market data. Kept for possible future reuse.

## Dashboard CSS

```css
      .market-section {
        width: min(1180px, 100%);
      }

      .section-heading {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 18px;
      }

      .eyebrow {
        margin: 0 0 6px;
        color: var(--muted);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }

      .section-heading h2 {
        margin: 0;
        font-size: 24px;
        letter-spacing: 0;
      }

      .as-of {
        flex: 0 0 auto;
        color: var(--muted);
        font-size: 14px;
      }

      .table-shell {
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: var(--shadow);
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
      }

      .widget-section {
        width: min(1180px, 100%);
        margin-top: 22px;
      }

      .tradingview-shell {
        min-height: 74px;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: var(--shadow);
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
      }

      tv-market-summary {
        display: block;
        width: 100%;
      }

      .calendar-section {
        width: min(1180px, 100%);
        margin-top: 22px;
      }

      .calendar-shell {
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: var(--shadow);
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
      }

      .calendar-shell iframe {
        display: block;
        width: 650px;
        max-width: none;
        height: 467px;
        border: 0;
      }

      .poweredBy {
        border-top: 1px solid var(--line);
        padding: 8px 12px;
        color: var(--muted);
        font-family: Arial, Helvetica, sans-serif;
        font-size: 11px;
      }

      .poweredBy a {
        color: #06529d;
        font-weight: 700;
      }

      body.theme-dark .poweredBy a {
        color: #6fb3ff;
      }

      .market-table {
        width: 100%;
        min-width: 980px;
        border-collapse: collapse;
        font-size: 14px;
      }

      .market-table th,
      .market-table td {
        height: 54px;
        border-bottom: 1px solid var(--line);
        padding: 0 16px;
        text-align: right;
        white-space: nowrap;
      }

      .market-table thead th {
        height: 48px;
        background: var(--surface-soft);
        color: var(--muted);
        font-size: 12px;
        font-weight: 800;
      }

      .market-table th:first-child,
      .market-table td:first-child {
        text-align: left;
      }

      .market-table tbody th {
        font-size: 15px;
        font-weight: 800;
      }

      .market-table tbody tr:last-child th,
      .market-table tbody tr:last-child td {
        border-bottom: 0;
      }

      .numeric {
        font-variant-numeric: tabular-nums;
      }

      .positive {
        color: #0f8a5f;
        font-weight: 800;
      }

      .negative {
        color: #c4483f;
        font-weight: 800;
      }

      body.theme-dark .positive {
        color: #47d59c;
      }

      body.theme-dark .negative {
        color: #ff7f75;
      }

```

## Dashboard Markup

```html
          <section class="market-section" aria-labelledby="market-title">
            <div class="section-heading">
              <div>
                <p class="eyebrow">KRX Open API</p>
                <h2 id="market-title">국내 지수 현황</h2>
              </div>
              <div class="as-of" id="market-as-of">기준일 확인 중</div>
            </div>

            <div class="table-shell">
              <table class="market-table">
                <thead>
                  <tr>
                    <th scope="col">지수</th>
                    <th scope="col">기준일</th>
                    <th scope="col">종가</th>
                    <th scope="col">거래대금</th>
                    <th scope="col">1일</th>
                    <th scope="col">1주일</th>
                    <th scope="col">1개월</th>
                    <th scope="col">3개월</th>
                    <th scope="col">6개월</th>
                    <th scope="col">12개월</th>
                    <th scope="col">YTD</th>
                  </tr>
                </thead>
                <tbody id="market-table-body">
              <tr>
                <th scope="row">코스피</th>
                <td>2026-06-26</td>
                <td class="numeric">8,411.21</td>
                <td class="numeric">54.00조</td>
                <td class="numeric negative">-5.81%</td>
                <td class="numeric negative">-7.08%</td>
                <td class="numeric positive">+4.52%</td>
                <td class="numeric positive">+54.04%</td>
                <td class="numeric positive">+103.68%</td>
                <td class="numeric positive">+173.13%</td>
                <td class="numeric positive">+99.59%</td>
              </tr>
              <tr>
                <th scope="row">코스닥</th>
                <td>2026-06-26</td>
                <td class="numeric">851.37</td>
                <td class="numeric">8.19조</td>
                <td class="numeric negative">-4.10%</td>
                <td class="numeric negative">-11.92%</td>
                <td class="numeric negative">-27.39%</td>
                <td class="numeric negative">-25.10%</td>
                <td class="numeric negative">-7.43%</td>
                <td class="numeric positive">+8.05%</td>
                <td class="numeric negative">-8.01%</td>
              </tr>
                </tbody>
              </table>
            </div>
          </section>

```

## Dashboard Client Script

```html
    <script>
      function formatIndexDate(value) {
        return value ? value.replace(/^(\d{4})(\d{2})(\d{2})$/, "$1-$2-$3") : "-";
      }

      function formatClose(value) {
        return Number(value).toLocaleString("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }

      function formatRate(value) {
        const rate = Number(value);
        const sign = rate > 0 ? "+" : "";
        return sign + rate.toFixed(2) + "%";
      }

      function rateClass(value) {
        const rate = Number(value);
        if (rate > 0) return "positive";
        if (rate < 0) return "negative";
        return "neutral";
      }

      function formatTradeValue(value) {
        return (Number(value) / 1000000000000).toLocaleString("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "조";
      }

      function renderMarketIndexes(items) {
        const tbody = document.querySelector("#market-table-body");
        const asOf = document.querySelector("#market-as-of");
        if (!tbody || !asOf || !Array.isArray(items) || items.length === 0) return;

        asOf.textContent = "기준일 " + formatIndexDate(items[0].basDd);
        tbody.innerHTML = items.map((item) => "\n              <tr>" +
          "\n                <th scope=\"row\">" + item.name + "</th>" +
          "\n                <td>" + formatIndexDate(item.basDd) + "</td>" +
          "\n                <td class=\"numeric\">" + formatClose(item.close) + "</td>" +
          "\n                <td class=\"numeric\">" + formatTradeValue(item.tradeValue) + "</td>" +
          "\n                <td class=\"numeric " + rateClass(item.returns.oneDay) + "\">" + formatRate(item.returns.oneDay) + "</td>" +
          "\n                <td class=\"numeric " + rateClass(item.returns.oneWeek) + "\">" + formatRate(item.returns.oneWeek) + "</td>" +
          "\n                <td class=\"numeric " + rateClass(item.returns.oneMonth) + "\">" + formatRate(item.returns.oneMonth) + "</td>" +
          "\n                <td class=\"numeric " + rateClass(item.returns.threeMonths) + "\">" + formatRate(item.returns.threeMonths) + "</td>" +
          "\n                <td class=\"numeric " + rateClass(item.returns.sixMonths) + "\">" + formatRate(item.returns.sixMonths) + "</td>" +
          "\n                <td class=\"numeric " + rateClass(item.returns.twelveMonths) + "\">" + formatRate(item.returns.twelveMonths) + "</td>" +
          "\n                <td class=\"numeric " + rateClass(item.returns.ytd) + "\">" + formatRate(item.returns.ytd) + "</td>" +
          "\n              </tr>").join("");
      }

      async function refreshMarketIndexes() {
        try {
          const response = await fetch("/api/index-data", { cache: "no-store" });
          if (!response.ok) throw new Error("KRX API " + response.status);
          const payload = await response.json();
          renderMarketIndexes(payload.items);
        } catch (error) {
          const asOf = document.querySelector("#market-as-of");
          if (asOf) asOf.textContent = asOf.textContent + " · 기존 데이터 표시 중";
        }
      }

      refreshMarketIndexes();
    </script>

```

## Server API Code

The current server still contains the KRX API implementation so it can be reconnected later. Snapshot below.

```js
const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");

loadEnv(path.join(__dirname, ".env"));

const PORT = Number(process.env.PORT || 4174);
const HOST = "127.0.0.1";
const ROOT_DIR = __dirname;
const KRX_AUTH_KEY = process.env.KRX_AUTH_KEY;

const ENDPOINTS = {
  kospi: "https://data-dbg.krx.co.kr/svc/apis/idx/kospi_dd_trd",
  kosdaq: "https://data-dbg.krx.co.kr/svc/apis/idx/kosdaq_dd_trd",
};

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

function loadEnv(filePath) {
  try {
    const text = require("node:fs").readFileSync(filePath, "utf8");
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const equals = trimmed.indexOf("=");
      if (equals === -1) continue;
      const key = trimmed.slice(0, equals).trim();
      const value = trimmed.slice(equals + 1).trim();
      if (!process.env[key]) process.env[key] = value;
    }
  } catch {
    // .env is optional. Use .env.example as the template.
  }
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function koreaToday() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return new Date(Number(map.year), Number(map.month) - 1, Number(map.day));
}

function toBasDd(date) {
  return String(date.getFullYear()) + pad(date.getMonth() + 1) + pad(date.getDate());
}

function parseBasDd(value) {
  return new Date(Number(value.slice(0, 4)), Number(value.slice(4, 6)) - 1, Number(value.slice(6, 8)));
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function addMonths(date, months) {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

function toNumber(value) {
  return Number(String(value || "").replaceAll(",", ""));
}

async function fetchIndexRow(kind, basDd) {
  if (!KRX_AUTH_KEY) throw new Error("KRX_AUTH_KEY is missing. Create .env from .env.example.");

  const response = await fetch(ENDPOINTS[kind] + "?basDd=" + basDd, {
    headers: { AUTH_KEY: KRX_AUTH_KEY },
  });
  if (!response.ok) throw new Error(kind + " " + basDd + " " + response.status);

  const json = await response.json();
  const targetName = kind === "kospi" ? "코스피" : "코스닥";
  const row = (json.OutBlock_1 || []).find((item) => item.IDX_NM === targetName && item.CLSPRC_IDX);
  if (!row) return null;

  return {
    kind,
    name: targetName,
    basDd: row.BAS_DD,
    close: toNumber(row.CLSPRC_IDX),
    tradeValue: toNumber(row.ACC_TRDVAL),
  };
}

async function findTradingRow(kind, startDate, maxBack = 45) {
  for (let i = 0; i <= maxBack; i += 1) {
    const row = await fetchIndexRow(kind, toBasDd(addDays(startDate, -i)));
    if (row) return row;
  }
  throw new Error("No trading row found for " + kind);
}

async function buildIndex(kind) {
  const latest = await findTradingRow(kind, koreaToday(), 30);
  const latestDate = parseBasDd(latest.basDd);
  const targets = {
    oneDay: addDays(latestDate, -1),
    oneWeek: addDays(latestDate, -7),
    oneMonth: addMonths(latestDate, -1),
    threeMonths: addMonths(latestDate, -3),
    sixMonths: addMonths(latestDate, -6),
    twelveMonths: addMonths(latestDate, -12),
    ytd: new Date(latestDate.getFullYear() - 1, 11, 31),
  };

  const returns = {};
  const baseDates = {};
  for (const [key, targetDate] of Object.entries(targets)) {
    const base = await findTradingRow(kind, targetDate, 20);
    returns[key] = (latest.close / base.close - 1) * 100;
    baseDates[key] = base.basDd;
  }

  return { ...latest, returns, baseDates };
}

async function getIndexPayload() {
  return {
    generatedAt: new Date().toISOString(),
    items: [await buildIndex("kospi"), await buildIndex("kosdaq")],
  };
}

async function serveStatic(pathname, res) {
  const routePath = pathname === "/" ? "/dashboard.html" : pathname;
  const requestedPath = path.normalize(path.join(ROOT_DIR, decodeURIComponent(routePath)));
  const normalizedRoot = path.normalize(ROOT_DIR);

  if (!requestedPath.startsWith(normalizedRoot)) {
    res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Forbidden");
    return;
  }

  const data = await fs.readFile(requestedPath);
  const ext = path.extname(requestedPath).toLowerCase();
  res.writeHead(200, { "Content-Type": MIME_TYPES[ext] || "application/octet-stream" });
  res.end(data);
}

const server = http.createServer(async (req, res) => {
  try {
    const parsed = new URL(req.url, "http://" + HOST + ":" + PORT);
    if (parsed.pathname === "/api/index-data") {
      const payload = await getIndexPayload();
      res.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      });
      res.end(JSON.stringify(payload));
      return;
    }

    await serveStatic(parsed.pathname, res);
  } catch (error) {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(String(error.message || error));
  }
});

server.listen(PORT, HOST, () => {
  console.log("Lighthouse AMC dashboard: http://" + HOST + ":" + PORT + "/dashboard.html");
});

```
