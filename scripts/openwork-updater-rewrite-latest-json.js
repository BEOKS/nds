#!/usr/bin/env node
/**
 * openwork-updater-rewrite-latest-json.js
 *
 * Tauri Updater(latest.json) 파일을 Nexus 공개 URL로 치환하고,
 * signature 값이 누락되어 있으면 *.sig 파일 내용을 읽어 채웁니다.
 *
 * 사용 예:
 *   node ./scripts/openwork-updater-rewrite-latest-json.js \
 *     --in  /path/to/latest.json \
 *     --out /path/to/out.latest.json \
 *     --bundle-dir /path/to/src-tauri/target/.../bundle \
 *     --public-base-url https://repo.gabia.com/repository/raw-repository/nds/openwork-updater
 */

"use strict";

const fs = require("fs");
const path = require("path");

function die(message) {
  process.stderr.write(`오류: ${message}\n`);
  process.exit(1);
}

function parseArgs(argv) {
  const args = {
    inPath: "",
    outPath: "",
    bundleDir: "",
    publicBaseUrl: "",
  };

  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case "--in":
        args.inPath = argv[++i] || "";
        break;
      case "--out":
        args.outPath = argv[++i] || "";
        break;
      case "--bundle-dir":
        args.bundleDir = argv[++i] || "";
        break;
      case "--public-base-url":
        args.publicBaseUrl = argv[++i] || "";
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
    "  node ./scripts/openwork-updater-rewrite-latest-json.js --in <latest.json> --out <out.json> --bundle-dir <bundleDir> --public-base-url <url>",
    "",
    "옵션:",
    "  --in               입력 latest.json 경로",
    "  --out              출력 latest.json 경로",
    "  --bundle-dir        tauri build 산출물 bundle 디렉토리",
    "  --public-base-url   업로드 후 공개 접근 base URL (예: .../openwork-updater)",
  ].join("\n");
}

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function findFileRecursive(rootDir, fileName) {
  /** @type {string[]} */
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

function stripTrailingSlash(url) {
  return String(url || "").replace(/\/+$/, "");
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    process.stdout.write(`${usage()}\n`);
    return;
  }

  if (!args.inPath) die("--in이 필요합니다.");
  if (!args.outPath) die("--out이 필요합니다.");
  if (!args.bundleDir) die("--bundle-dir이 필요합니다.");
  if (!args.publicBaseUrl) die("--public-base-url이 필요합니다.");

  if (!fs.existsSync(args.inPath)) die(`입력 latest.json을 찾을 수 없습니다: ${args.inPath}`);
  if (!fs.existsSync(args.bundleDir) || !fs.statSync(args.bundleDir).isDirectory()) {
    die(`bundle 디렉토리를 찾을 수 없습니다: ${args.bundleDir}`);
  }

  const publicBaseUrl = stripTrailingSlash(args.publicBaseUrl);

  let raw;
  try {
    raw = fs.readFileSync(args.inPath, "utf8");
  } catch (e) {
    die(`입력 파일을 읽을 수 없습니다: ${String(e)}`);
  }

  let json;
  try {
    json = JSON.parse(raw);
  } catch (e) {
    die(`JSON 파싱 실패: ${String(e)}`);
  }

  if (!isObject(json)) die("latest.json 루트가 객체가 아닙니다.");
  if (!isObject(json.platforms)) die("latest.json에 platforms 객체가 없습니다.");

  for (const [platformKey, platform] of Object.entries(json.platforms)) {
    if (!isObject(platform)) {
      die(`platforms.${platformKey} 값이 객체가 아닙니다.`);
    }

    const urlStr = String(platform.url || "");
    const updateFileName = path.basename(urlStr);
    if (!updateFileName || updateFileName === "." || updateFileName === "/") {
      die(`platforms.${platformKey}.url에서 파일명을 추출할 수 없습니다: ${urlStr}`);
    }

    const updatePath = findFileRecursive(args.bundleDir, updateFileName);
    if (!updatePath) {
      die(`업데이트 파일을 bundle에서 찾을 수 없습니다: ${updateFileName}`);
    }

    const sigFileName = `${updateFileName}.sig`;
    let sigPath = findFileRecursive(args.bundleDir, sigFileName);

    // 혹시 signature에 파일명이 들어있으면 그것도 후보로 시도합니다.
    if (!sigPath && typeof platform.signature === "string" && platform.signature.endsWith(".sig")) {
      const signatureFileNameHint = path.basename(platform.signature);
      if (signatureFileNameHint) {
        sigPath = findFileRecursive(args.bundleDir, signatureFileNameHint);
      }
    }

    if (sigPath) {
      const sig = fs.readFileSync(sigPath, "utf8").trim();
      if (sig) {
        platform.signature = sig;
      }
    }

    platform.url = `${publicBaseUrl}/${platformKey}/${updateFileName}`;
  }

  fs.writeFileSync(args.outPath, `${JSON.stringify(json, null, 2)}\n`);
}

main();

