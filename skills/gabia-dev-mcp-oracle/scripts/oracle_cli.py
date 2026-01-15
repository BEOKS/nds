#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v or None


def _require_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise SystemExit(f"[ERROR] Missing required env: {name}")
    return v


def _oracle_config() -> dict[str, str]:
    host = _require_env("ORACLE_HOST")
    user = _require_env("ORACLE_USERNAME")
    password = _require_env("ORACLE_PASSWORD")
    port = _env("ORACLE_PORT") or "1521"
    sid = _env("ORACLE_SID") or "DEVGABIA"
    service = _env("ORACLE_SERVICE_NAME")
    return {
        "host": host,
        "port": port,
        "sid": sid,
        "service": service or "",
        "username": user,
        "password": password,
    }


def _jdbc_url(cfg: dict[str, str]) -> str:
    if cfg.get("service"):
        return f"jdbc:oracle:thin:@//{cfg['host']}:{cfg['port']}/{cfg['service']}"
    return f"jdbc:oracle:thin:@{cfg['host']}:{cfg['port']}:{cfg['sid']}"


def _find_ojdbc_jar() -> Path | None:
    env_path = _env("ORACLE_JDBC_JAR")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p.resolve()

    # Best-effort auto-discovery (common for dev machines using Gradle)
    gradle_cache = Path.home() / ".gradle" / "caches" / "modules-2" / "files-2.1"
    if not gradle_cache.exists():
        return None
    candidates = list(gradle_cache.rglob("ojdbc*.jar"))
    if not candidates:
        return None
    # Prefer newest by mtime
    return max(candidates, key=lambda p: p.stat().st_mtime).resolve()


JAVA_SRC = r"""
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.util.Locale;

public class OracleCli {
    private static String esc(String s) {
        if (s == null) return "";
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '\\\\': out.append("\\\\\\\\"); break;
                case '\"': out.append("\\\\\""); break;
                case '\\n': out.append("\\\\n"); break;
                case '\\r': out.append("\\\\r"); break;
                case '\\t': out.append("\\\\t"); break;
                default:
                    if (c < 0x20) out.append(String.format("\\\\u%04x", (int)c));
                    else out.append(c);
            }
        }
        return out.toString();
    }

    private static void appendJsonValue(StringBuilder sb, Object v) {
        if (v == null) {
            sb.append("null");
            return;
        }
        if (v instanceof Number) {
            sb.append(v.toString());
            return;
        }
        if (v instanceof Boolean) {
            sb.append(((Boolean)v) ? "true" : "false");
            return;
        }
        sb.append('\"').append(esc(v.toString())).append('\"');
    }

    private static String readAllStdin() throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int r;
        while ((r = System.in.read(buf)) != -1) {
            baos.write(buf, 0, r);
        }
        return baos.toString(StandardCharsets.UTF_8);
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.err.println("Usage: OracleCli <test|select> <jdbcUrl> <username> <password>");
            System.exit(2);
        }
        String mode = args[0];
        String jdbcUrl = args[1];
        String username = args[2];
        String password = args[3];

        if ("test".equals(mode)) {
            try (Connection c = DriverManager.getConnection(jdbcUrl, username, password)) {
                System.out.println("{\"connected\":true}");
                return;
            } catch (Exception e) {
                System.out.println("{\"connected\":false,\"error\":\"" + esc(e.getMessage()) + "\"}");
                System.exit(2);
                return;
            }
        }

        if (!"select".equals(mode)) {
            System.err.println("Unknown mode: " + mode);
            System.exit(2);
            return;
        }

        String query = readAllStdin();
        query = query == null ? "" : query.trim();
        if (query.endsWith(";")) query = query.substring(0, query.length() - 1).trim();
        String upper = query.toUpperCase(Locale.ROOT);
        if (!upper.startsWith("SELECT")) {
            System.out.println("{\"error\":\"Only SELECT queries are allowed\"}");
            System.exit(2);
            return;
        }

        try (Connection c = DriverManager.getConnection(jdbcUrl, username, password);
             Statement st = c.createStatement();
             ResultSet rs = st.executeQuery(query)) {

            ResultSetMetaData md = rs.getMetaData();
            int n = md.getColumnCount();
            String[] cols = new String[n];
            for (int i = 1; i <= n; i++) cols[i - 1] = md.getColumnLabel(i);

            StringBuilder sb = new StringBuilder();
            sb.append("{\"columns\":[");
            for (int i = 0; i < n; i++) {
                if (i > 0) sb.append(",");
                sb.append('\"').append(esc(cols[i])).append('\"');
            }
            sb.append("],\"rows\":[");

            int rowCount = 0;
            boolean firstRow = true;
            while (rs.next()) {
                if (!firstRow) sb.append(",");
                sb.append("{");
                for (int i = 1; i <= n; i++) {
                    if (i > 1) sb.append(",");
                    sb.append('\"').append(esc(cols[i - 1])).append("\":");
                    Object v = rs.getObject(i);
                    appendJsonValue(sb, v);
                }
                sb.append("}");
                firstRow = false;
                rowCount++;
            }
            sb.append("],\"rowCount\":").append(rowCount).append("}");
            System.out.println(sb.toString());
        } catch (Exception e) {
            System.out.println("{\"error\":\"" + esc(e.getMessage()) + "\"}");
            System.exit(2);
        }
    }
}
"""


def _run_java(mode: str, cfg: dict[str, str], query: str | None) -> int:
    jar = _find_ojdbc_jar()
    if not jar:
        raise SystemExit(
            "[ERROR] Oracle JDBC jar not found.\n"
            "Set ORACLE_JDBC_JAR to a local ojdbc*.jar, or install sqlplus and use --engine sqlplus."
        )
    if not shutil.which("java") or not shutil.which("javac"):
        raise SystemExit("[ERROR] java/javac not found. Install a JDK or use --engine sqlplus.")

    with tempfile.TemporaryDirectory(prefix="oracle-cli-") as td:
        td_path = Path(td)
        src = td_path / "OracleCli.java"
        src.write_text(JAVA_SRC, encoding="utf-8")

        cp = f"{jar}"
        compile_proc = subprocess.run(
            ["javac", "-cp", cp, str(src)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if compile_proc.returncode != 0:
            raise SystemExit(f"[ERROR] javac failed:\n{compile_proc.stderr}")

        jdbc = _jdbc_url(cfg)
        run_cp = f"{td_path}:{jar}"
        stdin_data = (query or "").encode("utf-8")
        run_proc = subprocess.run(
            ["java", "-cp", run_cp, "OracleCli", mode, jdbc, cfg["username"], cfg["password"]],
            input=stdin_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        sys.stdout.write(run_proc.stdout.decode("utf-8", errors="replace"))
        if run_proc.returncode != 0 and run_proc.stderr:
            sys.stderr.write(run_proc.stderr.decode("utf-8", errors="replace"))
        return run_proc.returncode


def _sqlplus_login(cfg: dict[str, str]) -> str:
    connect = f"{cfg['host']}:{cfg['port']}/{cfg['service']}" if cfg.get("service") else f"{cfg['host']}:{cfg['port']}:{cfg['sid']}"
    return f"{cfg['username']}/{cfg['password']}@{connect}"


def _run_sqlplus(sql: str, cfg: dict[str, str]) -> int:
    if not shutil.which("sqlplus"):
        raise SystemExit("[ERROR] sqlplus not found. Install sqlplus or use --engine jdbc with ORACLE_JDBC_JAR.")
    login = _sqlplus_login(cfg)
    proc = subprocess.run(
        ["sqlplus", "-s", "-L", login],
        input=sql,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0 and proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


def _normalize_query(query: str) -> str:
    q = query.strip()
    if q.endswith(";"):
        q = q[:-1].strip()
    if not q.upper().startswith("SELECT"):
        raise SystemExit("[ERROR] Only SELECT queries are allowed.")
    return q


def cmd_test(args: argparse.Namespace) -> None:
    cfg = _oracle_config()
    engine = args.engine or "auto"

    if engine in ("auto", "jdbc"):
        try:
            rc = _run_java("test", cfg, None)
            raise SystemExit(0 if rc == 0 else rc)
        except SystemExit:
            if engine == "jdbc":
                raise

    # Fallback to sqlplus
    sql = "set heading off feedback off pagesize 0 verify off echo off\nselect 1 from dual;\nexit;\n"
    rc = _run_sqlplus(sql, cfg)
    raise SystemExit(0 if rc == 0 else rc)


def cmd_select(args: argparse.Namespace) -> None:
    cfg = _oracle_config()
    engine = args.engine or "auto"

    if args.query is not None:
        query = args.query
    elif args.query_file is not None:
        query = Path(args.query_file).read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            raise SystemExit("[ERROR] Provide --query/--query-file or pipe SQL via stdin.")
        query = sys.stdin.read()

    query = _normalize_query(query)

    if engine in ("auto", "jdbc"):
        try:
            rc = _run_java("select", cfg, query)
            raise SystemExit(0 if rc == 0 else rc)
        except SystemExit:
            if engine == "jdbc":
                raise

    # sqlplus fallback (prints plain text)
    sql = (
        "set pagesize 50000 linesize 32767 trimspool on feedback off verify off echo off\n"
        f"{query};\nexit;\n"
    )
    rc = _run_sqlplus(sql, cfg)
    raise SystemExit(0 if rc == 0 else rc)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Oracle CLI (no MCP required)")
    p.add_argument("--engine", choices=["auto", "jdbc", "sqlplus"], help="Execution engine (default: auto)")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("test", help="Test Oracle connection")
    t.set_defaults(func=cmd_test)

    s = sub.add_parser("select", help="Execute SELECT query")
    s.add_argument("--query", help="SELECT query string")
    s.add_argument("--query-file", help="Path to a .sql file")
    s.set_defaults(func=cmd_select)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

