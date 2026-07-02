const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");
const { spawn } = require("node:child_process");

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
  ".json": "application/json; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

const VALID_NEWS_LABELS = new Set(["high", "medium", "low", "exclude"]);
const NEWS_LABEL_TEXT = { high: "높음", medium: "보통", low: "낮음", exclude: "제외" };

// 헤게모니 국면 분류 스냅샷. 현재는 커밋된 정적 JSON을 그대로 서빙한다.
// 추후 financial.db 가 온라인 DB로 이전되면, 이 한 군데만 해당 DB를 조회해
// 동일한 형태의 payload 를 반환하도록 바꾸면 프런트엔드는 그대로 동작한다.
const PHASE_DATA_FILE = path.join(__dirname, "data", "phase-classification.json");
const PHASE_GENERATOR = path.join(__dirname, "scripts", "generate-phase-data.py");

// 국면 분류 스냅샷을 다시 생성한다(시가총액 등 최신 재계산). financial.db 와
// Python 이 있는 PC에서만 성공한다. PYTHON 환경변수로 실행 파일을 지정할 수 있다.
function runPhaseGenerator() {
  return new Promise((resolve, reject) => {
    const py = process.env.PYTHON || "python";
    const child = spawn(py, [PHASE_GENERATOR], { cwd: __dirname });
    let stderr = "";
    child.stdout.on("data", () => {});
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (err) => reject(new Error("생성기 실행 실패: " + err.message)));
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error("생성기 종료 코드 " + code + (stderr ? "\n" + stderr.slice(-600) : "")));
    });
  });
}

// 전자·닉스 시가총액 비중 스냅샷 (modules/weight-check 가 생성). 정적 JSON 서빙.
const WEIGHT_DATA_FILE = path.join(__dirname, "data", "weight-check.json");

// 상대수익률 추이 스냅샷 (modules/relative-return 가 엑셀에서 생성).
const RELRET_DATA_FILE = path.join(__dirname, "data", "relative-return.json");
const RELRET_GENERATOR = path.join(__dirname, "modules", "relative-return", "collect.py");

// 상대수익률 스냅샷을 엑셀에서 다시 생성한다(Python + 엑셀 파일이 있는 PC에서만 성공).
function runRelRetGenerator() {
  return new Promise((resolve, reject) => {
    const py = process.env.PYTHON || "python";
    const child = spawn(py, [RELRET_GENERATOR], { cwd: __dirname });
    let stderr = "";
    child.stdout.on("data", () => {});
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (err) => reject(new Error("생성기 실행 실패: " + err.message)));
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error("생성기 종료 코드 " + code + (stderr ? "\n" + stderr.slice(-600) : "")));
    });
  });
}

// 뉴스플로우 스냅샷 (modules/news-flow 가 생성: RSS + 크롤).
const NEWS_DATA_FILE = path.join(__dirname, "data", "news-flow.json");
const NEWS_LABELS_FILE = path.join(__dirname, "data", "news-labels.json");
const NEWS_GENERATOR = path.join(__dirname, "modules", "news-flow", "collect.py");

// 뉴스 스냅샷을 다시 수집한다(RSS + 크롤). 인터넷 + Python + 봇 소스 파일이 있는
// PC에서만 성공한다. PYTHON 환경변수로 실행 파일을 지정할 수 있다.
function runNewsCollector() {
  return new Promise((resolve, reject) => {
    const py = process.env.PYTHON || "python";
    const child = spawn(py, [NEWS_GENERATOR], { cwd: __dirname });
    let stderr = "";
    child.stdout.on("data", () => {});
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (err) => reject(new Error("수집기 실행 실패: " + err.message)));
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error("수집기 종료 코드 " + code + (stderr ? "\n" + stderr.slice(-600) : "")));
    });
  });
}

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

function sendJson(res, status, payload) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(JSON.stringify(payload));
}

function nowKstIso() {
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return map.year + "-" + map.month + "-" + map.day + "T" + map.hour + ":" + map.minute + ":" + map.second + "+0900";
}

async function readJsonObject(filePath) {
  try {
    const text = await fs.readFile(filePath, "utf8");
    const data = JSON.parse(text);
    return data && typeof data === "object" && !Array.isArray(data) ? data : {};
  } catch (error) {
    if (error.code === "ENOENT") return {};
    throw error;
  }
}

async function writeJsonObject(filePath, data) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function readRequestJson(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk.toString();
      if (body.length > 64 * 1024) {
        reject(new Error("요청 본문이 너무 큽니다."));
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error("JSON 형식이 올바르지 않습니다."));
      }
    });
    req.on("error", reject);
  });
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

async function saveNewsLabel(req, res) {
  const input = await readRequestJson(req);
  const articleId = String(input.article_id || "").trim();
  const label = String(input.label || "").trim();
  if (!/^[a-f0-9]{16}$/i.test(articleId)) {
    sendJson(res, 400, { error: "article_id가 올바르지 않습니다." });
    return;
  }

  const labels = await readJsonObject(NEWS_LABELS_FILE);
  if (label === "clear") {
    delete labels[articleId];
  } else {
    if (!VALID_NEWS_LABELS.has(label)) {
      sendJson(res, 400, { error: "label은 high, medium, low, exclude, clear 중 하나여야 합니다." });
      return;
    }
    labels[articleId] = {
      label,
      label_text: NEWS_LABEL_TEXT[label],
      reason: String(input.reason || "사용자 라벨").slice(0, 200),
      title: String(input.title || "").slice(0, 300),
      url: String(input.url || "").slice(0, 1000),
      source: String(input.source || "").slice(0, 120),
      updated_at: nowKstIso(),
    };
  }

  await writeJsonObject(NEWS_LABELS_FILE, labels);
  sendJson(res, 200, { ok: true, labels_count: Object.keys(labels).length, labels });
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
    if (parsed.pathname === "/api/phase/refresh") {
      if (req.method !== "POST") {
        res.writeHead(405, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Method Not Allowed");
        return;
      }
      await runPhaseGenerator();
      const data = await fs.readFile(PHASE_DATA_FILE);
      res.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      });
      res.end(data);
      return;
    }

    if (parsed.pathname === "/api/phase") {
      const data = await fs.readFile(PHASE_DATA_FILE);
      res.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      });
      res.end(data);
      return;
    }

    if (parsed.pathname === "/api/weight") {
      const data = await fs.readFile(WEIGHT_DATA_FILE);
      res.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      });
      res.end(data);
      return;
    }

    if (parsed.pathname === "/api/relative-return/refresh") {
      if (req.method !== "POST") {
        res.writeHead(405, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Method Not Allowed");
        return;
      }
      await runRelRetGenerator();
      const data = await fs.readFile(RELRET_DATA_FILE);
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
      res.end(data);
      return;
    }

    if (parsed.pathname === "/api/relative-return") {
      const data = await fs.readFile(RELRET_DATA_FILE);
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
      res.end(data);
      return;
    }

    if (parsed.pathname === "/api/news/refresh") {
      if (req.method !== "POST") {
        res.writeHead(405, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Method Not Allowed");
        return;
      }
      await runNewsCollector();
      const data = await fs.readFile(NEWS_DATA_FILE);
      res.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      });
      res.end(data);
      return;
    }

    if (parsed.pathname === "/api/news/labels") {
      if (req.method === "GET") {
        const labels = await readJsonObject(NEWS_LABELS_FILE);
        sendJson(res, 200, { labels_count: Object.keys(labels).length, labels });
        return;
      }
      if (req.method === "POST") {
        await saveNewsLabel(req, res);
        return;
      }
      res.writeHead(405, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Method Not Allowed");
      return;
    }

    if (parsed.pathname === "/api/news") {
      const data = await fs.readFile(NEWS_DATA_FILE);
      res.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      });
      res.end(data);
      return;
    }

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
