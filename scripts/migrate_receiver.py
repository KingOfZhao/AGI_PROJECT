#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 迁移接收端
在目标机器上运行此脚本，等待源机器推送迁移包

使用方式：
    python3 migrate_receiver.py [--port 5003] [--install-dir ~/AGI-实践器]

功能：
  1. 接收迁移包（分块上传）
  2. 解压并自动安装
  3. 拉取所需Ollama模型
  4. 验证并启动AGI服务
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)



import os
import sys
import json
import time
import shutil
import zipfile
import platform
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# 配置
DEFAULT_PORT = 5003
RECEIVE_DIR = Path(__file__).parent / "migrate_received"
INSTALL_DIR = Path(os.environ.get("AGI_INSTALL_DIR", str(Path.home() / "AGI-实践器")))

# 状态
_status = {
    "state": "waiting",  # waiting | receiving | installing | ready | error
    "progress": 0,
    "message": "等待迁移包...",
    "received_files": {},
    "install_log": []
}
_status_lock = threading.Lock()


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    print(entry)
    with _status_lock:
        _status["install_log"].append(entry)
        if len(_status["install_log"]) > 200:
            _status["install_log"] = _status["install_log"][-200:]


class MigrateHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/status':
            self._json_response(200, {
                "state": _status["state"],
                "progress": _status["progress"],
                "message": _status["message"],
                "hostname": platform.node(),
                "os": platform.system(),
                "arch": platform.machine(),
                "install_dir": str(INSTALL_DIR),
                "log_tail": _status["install_log"][-20:]
            })
        elif self.path == '/':
            self._json_response(200, {
                "service": "AGI v13.3 Migration Receiver",
                "version": "1.0",
                "status": _status["state"]
            })
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if self.path == '/upload':
            self._handle_upload(body)
        elif self.path == '/install':
            self._handle_install(body)
        else:
            self._json_response(404, {"error": "not found"})

    def _handle_upload(self, body):
        """接收迁移包分块"""
        try:
            data = json.loads(body)
            chunk_idx = data["chunk_idx"]
            hex_data = data["data"]
            total_size = data["total_size"]
            filename = data["filename"]

            RECEIVE_DIR.mkdir(parents=True, exist_ok=True)
            filepath = RECEIVE_DIR / filename

            chunk_bytes = bytes.fromhex(hex_data)

            mode = 'ab' if chunk_idx > 0 else 'wb'
            with open(filepath, mode) as f:
                f.write(chunk_bytes)

            current_size = filepath.stat().st_size
            pct = int(current_size / total_size * 100)

            with _status_lock:
                _status["state"] = "receiving"
                _status["progress"] = pct
                _status["message"] = f"接收中... {current_size/1024/1024:.1f}/{total_size/1024/1024:.1f}MB"
                _status["received_files"][filename] = {
                    "size": current_size,
                    "total": total_size,
                    "complete": current_size >= total_size
                }

            log(f"接收 chunk {chunk_idx}: {len(chunk_bytes)} bytes ({pct}%)")
            self._json_response(200, {"success": True, "progress": pct})

        except Exception as e:
            log(f"上传错误: {e}")
            self._json_response(500, {"error": str(e)})

    def _handle_install(self, body):
        """触发安装"""
        try:
            data = json.loads(body)
            filename = data.get("filename", "")
            filepath = RECEIVE_DIR / filename

            if not filepath.exists():
                self._json_response(400, {"error": f"文件不存在: {filename}"})
                return

            with _status_lock:
                _status["state"] = "installing"
                _status["progress"] = 0
                _status["message"] = "开始安装..."

            # 在后台线程执行安装
            thread = threading.Thread(target=self._do_install, args=(filepath,), daemon=True)
            thread.start()

            self._json_response(200, {"success": True, "message": "安装已启动"})

        except Exception as e:
            log(f"安装触发错误: {e}")
            self._json_response(500, {"error": str(e)})

    def _do_install(self, pkg_path):
        """执行安装（后台）"""
        try:
            # 1. 解压
            log("解压迁移包...")
            extract_dir = RECEIVE_DIR / "extracted"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True)

            with zipfile.ZipFile(pkg_path, 'r') as zf:
                zf.extractall(extract_dir)

            with _status_lock:
                _status["progress"] = 20
                _status["message"] = "解压完成，复制文件..."

            # 2. 复制到安装目录
            log(f"复制到 {INSTALL_DIR}...")
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)

            for item in extract_dir.iterdir():
                if item.name in ('install.py', 'README.md'):
                    continue
                dst = INSTALL_DIR / item.name
                if item.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(item, dst)
                else:
                    shutil.copy2(item, dst)

            with _status_lock:
                _status["progress"] = 40
                _status["message"] = "创建虚拟环境..."

            # 3. 虚拟环境
            log("创建虚拟环境...")
            venv_dir = INSTALL_DIR / "venv"
            if not venv_dir.exists():
                subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

            pip = str(venv_dir / ("Scripts" if platform.system() == "Windows" else "bin") / "pip")
            subprocess.run([pip, "install", "flask", "flask-cors", "openai", "numpy", "requests"],
                          capture_output=True, check=True)

            with _status_lock:
                _status["progress"] = 60
                _status["message"] = "安装依赖完成，检查模型..."

            # 4. 模型
            log("检查Ollama模型...")
            manifest_path = extract_dir / "model_manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                for model in manifest.get("required", []):
                    log(f"拉取模型: {model}")
                    with _status_lock:
                        _status["message"] = f"拉取模型 {model}..."
                    result = subprocess.run(["ollama", "pull", model],
                                           capture_output=True, text=True, timeout=600)
                    if result.returncode == 0:
                        log(f"  ✓ {model} 就绪")
                    else:
                        log(f"  ⚠ {model} 拉取失败: {result.stderr[:100]}")

            with _status_lock:
                _status["progress"] = 90
                _status["message"] = "验证安装..."

            # 5. 验证
            log("验证安装...")
            python = str(venv_dir / ("Scripts" if platform.system() == "Windows" else "bin") / "python")
            result = subprocess.run(
                [python, "-c", "import flask; import openai; print('ok')"],
                capture_output=True, text=True
            )
            if "ok" in (result.stdout or ""):
                log("✓ 依赖验证通过")
            else:
                log("⚠ 部分依赖可能缺失")

            with _status_lock:
                _status["state"] = "ready"
                _status["progress"] = 100
                _status["message"] = f"安装完成! 目录: {INSTALL_DIR}"

            log(f"✓ 迁移安装完成: {INSTALL_DIR}")

        except Exception as e:
            log(f"安装失败: {e}")
            with _status_lock:
                _status["state"] = "error"
                _status["progress"] = -1
                _status["message"] = f"安装失败: {e}"

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        pass  # 静默HTTP日志


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AGI v13.3 Migration Receiver")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--install-dir', type=str, default=str(INSTALL_DIR))
    args = parser.parse_args()

    global INSTALL_DIR
    INSTALL_DIR = Path(args.install_dir)

    print("=" * 50)
    print("  AGI v13.3 Migration Receiver")
    print("=" * 50)
    print(f"  监听端口: {args.port}")
    print(f"  安装目录: {INSTALL_DIR}")
    print(f"  系统: {platform.system()} {platform.machine()}")
    print(f"  Python: {platform.python_version()}")
    print("=" * 50)
    print("  等待源机器推送迁移包...")
    print()

    server = HTTPServer(('0.0.0.0', args.port), MigrateHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    main()
