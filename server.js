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
