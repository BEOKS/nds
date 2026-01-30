#!/usr/bin/env node
/**
 * publish-openwork-updater.node.js
 *
 * OpenWork(Tauri) Updater 산출물(latest.json + update bundle)을 Nexus(raw-repository)에 업로드합니다.
 * (macOS/Windows 공용: Node.js만 있으면 동작)
 *
 * 업로드 구조(기본):
 *   <NEXUS_BASE_URL>/openwork-updater/<platform>/latest.json
 *   <NEXUS_BASE_URL>/openwork-updater/<platform>/<update-file>
 *   <NEXUS_BASE_URL>/openwork-updater/<platform>/<update-file>.sig (옵션)
 */

"use strict";

const fs = require("fs");
const http = require("http");
const https = require("https");
const path = require("path");

function die(message) {
  process.stderr.write(`오류: ${message}\n`);
  process.exit(1);
}

function info(message) {
  process.stdout.write(`[INFO] ${message}\n`);
}

function warn(message) {
  process.stdout.write(`[WARN] ${message}\n`);
}

function stripTrailingSlash(url) {
  return String(url || "").replace(/\/+$/, "");
}

function stripSlashes(p) {
  return String(p || "").replace(/^\/+/, "").replace(/\/+$/, "");
}

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseArgs(argv) {
  const args = {
    bundleDir: "",
    latestJson: "",
    nexusBaseUrl: process.env.NDS_NEXUS_URL || "https://repo.gabia.com/repository/raw-repository/nds",
    destPrefix: "openwork-updater",
    username: process.env.NDS_NEXUS_USERNAME || process.env.NEXUS_USERNAME || "",
    password: process.env.NDS_NEXUS_PASSWORD || process.env.NEXUS_PASSWORD || "",
    dryRun: false,
  };

  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case "--bundle-dir":
        args.bundleDir = argv[++i] || "";
        break;
      case "--latest-json":
        args.latestJson = argv[++i] || "";
        break;
      case "--nexus-base-url":
        args.nexusBaseUrl = argv[++i] || "";
        break;
      case "--dest-prefix":
        args.destPrefix = argv[++i] || "";
        break;
      case "--username":
        args.username = argv[++i] || "";
        break;
      case "--password":
        args.password = argv[++i] || "";
        break;
      case "--dry-run":
        args.dryRun = true;
        break;
      case "-h":
      case "--help":
        args.help = true;
        break;
      default:
        die(`알 수 없는 인자: ${a}`);
    }
  }

  return args;
}

function usage() {
  return [
    "사용법:",
    "  node ./scripts/publish-openwork-updater.node.js --bundle-dir <bundleDir> [옵션]",
    "",
    "옵션:",
    "  --bundle-dir <path>        tauri build 산출물 bundle 디렉토리 (필수)",
    "  --latest-json <path>       latest.json 경로를 직접 지정(기본: bundle-dir 하위 검색)",
    "  --nexus-base-url <url>     Nexus raw repository base URL (기본: $NDS_NEXUS_URL)",
    "  --dest-prefix <path>       업로드 prefix (기본: openwork-updater)",
    "  --username <u>             Nexus 사용자명 (기본: $NDS_NEXUS_USERNAME 또는 $NEXUS_USERNAME)",
    "  --password <p>             Nexus 비밀번호 (기본: $NDS_NEXUS_PASSWORD 또는 $NEXUS_PASSWORD)",
    "  --dry-run                  실제 업로드 없이 업로드 대상만 출력",
  ].join("\n");
}

function findLatestJson(bundleDir) {
  /** @type {string[]} */
  const found = [];
  const stack = [bundleDir];
  while (stack.length > 0) {
    const current = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      const full = path.join(current, ent.name);
      if (ent.isDirectory()) {
        stack.push(full);
        continue;
      }
      if (ent.isFile() && ent.name === "latest.json") {
        found.push(full);
      }
    }
  }

  if (found.length === 0) return "";
  if (found.length > 1) {
    die(`latest.json 후보가 여러 개입니다. --latest-json로 정확히 지정하세요.\n- ${found.join("\n- ")}`);
  }
  return found[0];
}

function findFileRecursive(rootDir, fileName) {
  const stack = [rootDir];
  while (stack.length > 0) {
    const current = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      const full = path.join(current, ent.name);
      if (ent.isDirectory()) {
        stack.push(full);
        continue;
      }
      if (ent.isFile() && ent.name === fileName) {
        return full;
      }
    }
  }
  return "";
}

function readJson(filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  return JSON.parse(raw);
}

function buildAuthHeader(username, password) {
  const token = Buffer.from(`${username}:${password}`, "utf8").toString("base64");
  return `Basic ${token}`;
}

function putStream(urlStr, authHeader, contentType, filePath, dryRun) {
  const u = new URL(urlStr);
  const mod = u.protocol === "https:" ? https : http;

  const stat = fs.statSync(filePath);
  const headers = {
    Authorization: authHeader,
    "Content-Length": stat.size,
    "Content-Type": contentType,
  };

  if (dryRun) {
    info(`DRY_RUN: ${filePath} -> ${urlStr}`);
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const req = mod.request(
      {
        method: "PUT",
        protocol: u.protocol,
        hostname: u.hostname,
        port: u.port,
        path: `${u.pathname}${u.search}`,
        headers,
      },
      (res) => {
        const chunks = [];
        res.on("data", (d) => chunks.push(d));
        res.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve();
            return;
          }
          reject(new Error(`PUT 실패: ${urlStr} (${res.statusCode}) ${body}`.trim()));
        });
      },
    );

    req.on("error", reject);
    const rs = fs.createReadStream(filePath);
    rs.on("error", reject);
    rs.pipe(req);
  });
}

function putBuffer(urlStr, authHeader, contentType, buffer, dryRun) {
  const u = new URL(urlStr);
  const mod = u.protocol === "https:" ? https : http;

  const headers = {
    Authorization: authHeader,
    "Content-Length": buffer.length,
    "Content-Type": contentType,
  };

  if (dryRun) {
    info(`DRY_RUN: <buffer ${buffer.length} bytes> -> ${urlStr}`);
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const req = mod.request(
      {
        method: "PUT",
        protocol: u.protocol,
        hostname: u.hostname,
        port: u.port,
        path: `${u.pathname}${u.search}`,
        headers,
      },
      (res) => {
        const chunks = [];
        res.on("data", (d) => chunks.push(d));
        res.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve();
            return;
          }
          reject(new Error(`PUT 실패: ${urlStr} (${res.statusCode}) ${body}`.trim()));
        });
      },
    );
    req.on("error", reject);
    req.write(buffer);
    req.end();
  });
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    process.stdout.write(`${usage()}\n`);
    return;
  }

  if (!args.bundleDir) die("--bundle-dir는 필수입니다.");
  if (!fs.existsSync(args.bundleDir) || !fs.statSync(args.bundleDir).isDirectory()) {
    die(`bundle 디렉토리를 찾을 수 없습니다: ${args.bundleDir}`);
  }

  if (!args.username || !args.password) {
    die("Nexus 인증 정보가 필요합니다. (--username/--password 또는 NDS_NEXUS_USERNAME/NDS_NEXUS_PASSWORD)");
  }

  const nexusBaseUrl = stripTrailingSlash(args.nexusBaseUrl);
  const destPrefix = stripSlashes(args.destPrefix);
  const publicBaseUrl = `${nexusBaseUrl}/${destPrefix}`;

  const latestJsonPath = args.latestJson ? args.latestJson : findLatestJson(args.bundleDir);
  if (!latestJsonPath) die("bundle 하위에서 latest.json을 찾을 수 없습니다. --latest-json로 지정하세요.");
  if (!fs.existsSync(latestJsonPath)) die(`latest.json을 찾을 수 없습니다: ${latestJsonPath}`);

  info(`bundle: ${args.bundleDir}`);
  info(`latest.json: ${latestJsonPath}`);
  info(`public base: ${publicBaseUrl}`);

  const json = readJson(latestJsonPath);
  if (!isObject(json) || !isObject(json.platforms)) die("latest.json에 platforms 객체가 없습니다.");

  const authHeader = buildAuthHeader(args.username, args.password);

  // 1) latest.json을 Nexus URL로 rewrite + signature 보강
  /** @type {Array<{platform:string, updateFileName:string, updateFilePath:string, sigFilePath:string}>} */
  const manifest = [];

  for (const [platformKey, platform] of Object.entries(json.platforms)) {
    if (!isObject(platform)) die(`platforms.${platformKey} 값이 객체가 아닙니다.`);
    const updateUrlStr = String(platform.url || "");
    const updateFileName = path.basename(updateUrlStr);
    if (!updateFileName || updateFileName === "." || updateFileName === "/") {
      die(`platforms.${platformKey}.url에서 파일명을 추출할 수 없습니다: ${updateUrlStr}`);
    }

    const updateFilePath = findFileRecursive(args.bundleDir, updateFileName);
    if (!updateFilePath) die(`업데이트 파일을 bundle에서 찾을 수 없습니다: ${updateFileName}`);

    const sigFileName = `${updateFileName}.sig`;
    const sigFilePath = findFileRecursive(args.bundleDir, sigFileName);
    if (sigFilePath) {
      const sig = fs.readFileSync(sigFilePath, "utf8").trim();
      if (sig) platform.signature = sig;
    } else if (!platform.signature) {
      die(`signature 값을 찾을 수 없습니다: ${sigFileName}`);
    } else {
      warn(`signature 파일을 찾지 못했습니다(업로드는 생략): ${sigFileName}`);
    }

    platform.url = `${publicBaseUrl}/${platformKey}/${updateFileName}`;
    manifest.push({ platform: platformKey, updateFileName, updateFilePath, sigFilePath });
  }

  const latestJsonOut = Buffer.from(`${JSON.stringify(json, null, 2)}\n`, "utf8");

  // 2) 파일 업로드
  for (const item of manifest) {
    const destDir = `${publicBaseUrl}/${item.platform}`;
    const destUpdateUrl = `${destDir}/${item.updateFileName}`;
    const destSigUrl = `${destDir}/${item.updateFileName}.sig`;
    const destLatestUrl = `${destDir}/latest.json`;

    info(`platform: ${item.platform}`);
    await putStream(destUpdateUrl, authHeader, "application/octet-stream", item.updateFilePath, args.dryRun);
    if (item.sigFilePath) {
      await putStream(destSigUrl, authHeader, "text/plain", item.sigFilePath, args.dryRun);
    }
    await putBuffer(destLatestUrl, authHeader, "application/json", latestJsonOut, args.dryRun);
    info(`OK: ${destLatestUrl}`);
  }

  info("✅ 완료");
}

main().catch((e) => {
  die(String(e && e.message ? e.message : e));
});

