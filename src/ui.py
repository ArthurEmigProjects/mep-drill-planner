"""Local page for choosing an MEP IFC and extracting anchor points.

Run from the repo root:

    python -m src.ui

Then open http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from .extract_anchor_points import extract_from_ifc

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
UPLOADS = EXAMPLES / "uploads"
OUT_DIR = EXAMPLES / "out"
WEB = Path(__file__).resolve().parent / "web"
MAX_UPLOAD = 250 * 1024 * 1024

SAMPLE_CATALOG = {
    "zenodo-duplex-ventilation.ifc": {
        "title": "Duplex ventilation",
        "detail": "Zenodo · Teclaw 2024",
    },
    "zenodo-duplex-piping.ifc": {
        "title": "Duplex piping",
        "detail": "Zenodo · Teclaw 2024",
    },
    "buildingsmart-duplex-mep.ifc": {
        "title": "Duplex MEP",
        "detail": "buildingSMART community sample",
    },
}

_SCHEMA_RE = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", re.IGNORECASE)
_NAME_RE = re.compile(r"FILE_NAME\s*\(\s*'([^']*)'", re.IGNORECASE)


def ifcopenshell_ready() -> bool:
    try:
        import ifcopenshell  # noqa: F401
    except ImportError:
        return False
    return True


def format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def peek_ifc(path: Path) -> dict:
    with path.open("rb") as handle:
        header = handle.read(32768)
    text = header.decode("latin-1", errors="replace")
    schema = _SCHEMA_RE.search(text)
    internal = _NAME_RE.search(text)
    return {
        "schema": schema.group(1) if schema else None,
        "internal_name": internal.group(1) if internal else None,
        "is_ifc": b"ISO-10303-21" in header[:64],
    }


def display_name(path: Path, origin: str) -> str:
    if origin == "upload":
        return re.sub(r"^[0-9a-f]{8}-", "", path.name, count=1)
    return path.name


def describe(path: Path, origin: str) -> dict:
    meta = peek_ifc(path)
    label = display_name(path, origin)
    catalog = SAMPLE_CATALOG.get(label, {})
    stem = Path(label).stem.replace("-", " ").replace("_", " ")
    return {
        "id": f"{origin}:{path.name}",
        "name": label,
        "title": catalog.get("title", stem),
        "detail": catalog.get("detail", "Opened from this computer"),
        "origin": origin,
        "bytes": path.stat().st_size,
        "size": format_bytes(path.stat().st_size),
        "schema": meta["schema"],
        "internal_name": meta["internal_name"],
    }


def list_files() -> list[dict]:
    files: list[dict] = []
    if EXAMPLES.is_dir():
        for path in sorted(EXAMPLES.glob("*.ifc")):
            files.append(describe(path, "sample"))
    if UPLOADS.is_dir():
        for path in sorted(UPLOADS.glob("*.ifc"), key=lambda p: p.stat().st_mtime, reverse=True):
            files.append(describe(path, "upload"))
    return files


def resolve_file(file_id: str) -> Path:
    kind, sep, name = file_id.partition(":")
    if not sep or Path(name).name != name or not name.lower().endswith(".ifc"):
        raise ValueError("Unknown file")
    base = EXAMPLES if kind == "sample" else UPLOADS if kind == "upload" else None
    if base is None:
        raise ValueError("Unknown file")
    path = (base / name).resolve()
    if path.parent != base.resolve() or not path.is_file():
        raise ValueError("File not found")
    return path


def safe_upload_name(raw: str) -> str:
    base = Path(raw).name.strip() or "model.ifc"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    if not cleaned.lower().endswith(".ifc"):
        cleaned = f"{cleaned or 'model'}.ifc"
    return f"{uuid4().hex[:8]}-{cleaned}"


class AppHandler(BaseHTTPRequestHandler):
    server_version = "mep-drill-planner"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send_file(WEB / "index.html", "text/html; charset=utf-8")
            return
        if path == "/assets/styles.css":
            self._send_file(WEB / "styles.css", "text/css; charset=utf-8")
            return
        if path == "/assets/app.js":
            self._send_file(WEB / "app.js", "text/javascript; charset=utf-8")
            return
        if path == "/api/files":
            self._send_json({"files": list_files(), "ifcopenshell": ifcopenshell_ready()})
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/api/uploads":
            self._upload()
            return
        if path == "/api/extract":
            self._extract()
            return
        self.send_error(404)

    def _read_body(self, limit: int) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "Missing content length"}, 400)
            return None
        if length <= 0 or length > limit:
            self._send_json({"error": "File is empty or larger than 250 MB"}, 400)
            return None
        return self.rfile.read(length)

    def _upload(self) -> None:
        body = self._read_body(MAX_UPLOAD)
        if body is None:
            return
        if b"ISO-10303-21" not in body[:256]:
            self._send_json({"error": "That file is not an IFC (missing ISO-10303-21 header)."}, 400)
            return
        UPLOADS.mkdir(parents=True, exist_ok=True)
        name = safe_upload_name(self.headers.get("X-Filename", "model.ifc"))
        dest = UPLOADS / name
        dest.write_bytes(body)
        self._send_json({"file": describe(dest, "upload")})

    def _extract(self) -> None:
        body = self._read_body(64 * 1024)
        if body is None:
            return
        try:
            payload = json.loads(body.decode("utf-8"))
            path = resolve_file(str(payload["id"]))
        except (KeyError, ValueError, json.JSONDecodeError, UnicodeError):
            self._send_json({"error": "Choose an IFC file first."}, 400)
            return
        try:
            result = extract_from_ifc(path)
        except SystemExit as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        except Exception as exc:  # geometry libraries raise a wide set of errors
            self._send_json({"error": f"Could not read {path.name}: {exc}"}, 500)
            return
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"{path.stem}-points.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["count"] = len(result["points"])
        result["out"] = str(out.relative_to(ROOT))
        self._send_json(result)

    def _send_json(self, data: dict, status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), AppHandler)
    except OSError as exc:
        print(f"Could not listen on port {args.port}: {exc}", file=sys.stderr)
        return 1

    url = f"http://127.0.0.1:{args.port}/"
    print(f"IFC file selection → {url}", flush=True)
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
