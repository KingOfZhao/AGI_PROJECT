#!/usr/bin/env python3
"""CRM后端 — 静态文件 + API路由"""
import json, os, sys, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DEDUCTION_FILE = DATA_DIR / "deduction_export.json"

def load_db():
    if DEDUCTION_FILE.exists():
        with open(DEDUCTION_FILE) as f:
            return json.load(f)
    return {"deductions": [], "problems": [], "projects": []}

def save_db(db):
    db["exported_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(DEDUCTION_FILE, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

class CRMHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(Path(__file__).parent), **kw)
    
    def do_GET(self):
        if self.path == "/api/problems":
            db = load_db()
            # 前端期望纯数组, 同时挂deductions到window
            self._json(db.get("problems", []))
        elif self.path == "/api/projects":
            db = load_db()
            # 前端期望纯数组
            projects = {}
            for d in db.get("deductions", []):
                pid = d.get("project", "p_diepre")
                if pid not in projects:
                    projects[pid] = {"id": pid, "name": pid, "deductions": [], "done": 0, "queued": 0, "running": 0}
                projects[pid]["deductions"].append(d)
                st = d.get("status", "queued")
                if st in projects[pid]:
                    projects[pid][st] += 1
            self._json(list(projects.values()))
        elif self.path == "/api/deductions":
            db = load_db()
            self._json(db.get("deductions", []))
        elif self.path.startswith("/api/"):
            self._json({"error": "not found"}, 404)
        else:
            super().do_GET()
    
    def do_POST(self):
        db = load_db()
        
        if self.path == "/api/problems":
            body = self._body()
            prob = {
                "id": f"prob_{int(time.time())}",
                "title": body.get("title", ""),
                "description": body.get("description", ""),
                "severity": body.get("severity", "medium"),
                "status": "open",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            db.setdefault("problems", []).append(prob)
            save_db(db)
            self._json(prob)
        
        elif self.path.startswith("/api/problems/") and self.path.endswith("/resolve"):
            pid = self.path.split("/")[3]
            body = self._body()
            for p in db.get("problems", []):
                if p.get("id") == pid:
                    p["status"] = "resolved"
                    p["solution"] = body.get("solution", "")
                    p["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    break
            save_db(db)
            self._json({"ok": True})
        
        elif self.path.startswith("/api/deductions/") and self.path.endswith("/status"):
            did = self.path.split("/")[3]
            body = self._body()
            for d in db.get("deductions", []):
                if d.get("id") == did:
                    d["status"] = body.get("status", d.get("status", "queued"))
                    if body.get("status") == "done":
                        d["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    break
            save_db(db)
            self._json({"ok": True})
        
        else:
            self._json({"error": "not found"}, 404)
    
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    
    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def log_message(self, fmt, *args):
        print(f"[CRM] {args[0]}")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8890
    server = HTTPServer(("0.0.0.0", port), CRMHandler)
    print(f"CRM server on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
