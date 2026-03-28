#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 集群管理器 — 设备发现 · 一键迁移 · 分布式通讯 · 飞书集成

功能：
  1. 设备发现与管理（局域网扫描 + 手动添加）
  2. 一键迁移（打包模型引用+数据库+配置+技能→目标机器）
  3. 分布式推理（多设备协作，路由请求到不同节点）
  4. 飞书 OpenClaw 集成（Webhook Bot 双向通讯）
"""

import os
import sys
import json
import time
import socket
import sqlite3
import shutil
import hashlib
import zipfile
import threading
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "memory.db"
WORKSPACE_DIR = BASE_DIR / "workspace"
MIGRATE_DIR = BASE_DIR / "migrate_packages"
CLUSTER_CONFIG = BASE_DIR / "cluster_config.json"

# 默认端口
AGI_PORT = 5002
OLLAMA_PORT = 11434
RECEIVER_PORT = 5003

# ==================== 设备管理 ====================

class DeviceManager:
    """管理集群中的设备"""

    def __init__(self):
        self._devices = {}  # ip -> device_info
        self._lock = threading.Lock()
        self._load_config()

    def _load_config(self):
        """从配置文件加载设备列表"""
        if CLUSTER_CONFIG.exists():
            try:
                with open(CLUSTER_CONFIG, 'r') as f:
                    cfg = json.load(f)
                self._devices = cfg.get('devices', {})
                self._feishu_config = cfg.get('feishu', {})
            except Exception:
                self._devices = {}
                self._feishu_config = {}
        else:
            self._devices = {}
            self._feishu_config = {}

    def _save_config(self):
        """保存设备列表到配置文件"""
        cfg = {
            'devices': self._devices,
            'feishu': getattr(self, '_feishu_config', {}),
            'updated_at': datetime.now().isoformat()
        }
        with open(CLUSTER_CONFIG, 'w') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def get_local_ip(self):
        """获取本机局域网IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_local_info(self):
        """获取本机信息"""
        return {
            "ip": self.get_local_ip(),
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "os_version": platform.version(),
            "arch": platform.machine(),
            "python": platform.python_version(),
            "is_self": True
        }

    def add_device(self, ip, name="", os_type="auto", port=AGI_PORT):
        """手动添加设备"""
        with self._lock:
            device = {
                "ip": ip,
                "name": name or f"Device-{ip.split('.')[-1]}",
                "os": os_type,
                "port": port,
                "receiver_port": RECEIVER_PORT,
                "status": "unknown",
                "added_at": datetime.now().isoformat(),
                "last_seen": None,
                "ollama_status": "unknown",
                "agi_status": "unknown",
                "capabilities": {}
            }
            self._devices[ip] = device
            self._save_config()
            return device

    def remove_device(self, ip):
        """移除设备"""
        with self._lock:
            if ip in self._devices:
                del self._devices[ip]
                self._save_config()
                return True
            return False

    def list_devices(self):
        """列出所有设备"""
        local = self.get_local_info()
        devices = [{"ip": local["ip"], "name": f"{local['hostname']} (本机)",
                     "os": local["os"], "status": "online",
                     "is_self": True, "ollama_status": "checking",
                     "agi_status": "online"}]
        for ip, d in self._devices.items():
            d['is_self'] = False
            devices.append(d)
        return devices

    def _check_port(self, ip, port, timeout=2):
        """检查端口是否开放"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _check_ollama(self, ip, timeout=3):
        """检查Ollama是否运行"""
        try:
            import urllib.request
            req = urllib.request.Request(f"http://{ip}:{OLLAMA_PORT}/api/tags", method='GET')
            resp = urllib.request.urlopen(req, timeout=timeout)
            data = json.loads(resp.read().decode())
            models = [m.get('name', '') for m in data.get('models', [])]
            return {"status": "online", "models": models}
        except Exception:
            return {"status": "offline", "models": []}

    def _check_agi(self, ip, port=AGI_PORT, timeout=3):
        """检查AGI服务是否运行"""
        try:
            import urllib.request
            req = urllib.request.Request(f"http://{ip}:{port}/api/stats", method='GET')
            resp = urllib.request.urlopen(req, timeout=timeout)
            data = json.loads(resp.read().decode())
            return {"status": "online", "stats": data}
        except Exception:
            return {"status": "offline", "stats": {}}

    def _check_receiver(self, ip, port=RECEIVER_PORT, timeout=3):
        """检查迁移接收端是否运行"""
        try:
            import urllib.request
            req = urllib.request.Request(f"http://{ip}:{port}/status", method='GET')
            resp = urllib.request.urlopen(req, timeout=timeout)
            data = json.loads(resp.read().decode())
            return {"status": "online", "info": data}
        except Exception:
            return {"status": "offline", "info": {}}

    def probe_device(self, ip):
        """探测单个设备状态"""
        ollama = self._check_ollama(ip)
        agi = self._check_agi(ip)
        receiver = self._check_receiver(ip)

        is_online = ollama["status"] == "online" or agi["status"] == "online" or receiver["status"] == "online"

        with self._lock:
            if ip in self._devices:
                self._devices[ip].update({
                    "status": "online" if is_online else "offline",
                    "ollama_status": ollama["status"],
                    "agi_status": agi["status"],
                    "receiver_status": receiver["status"],
                    "ollama_models": ollama.get("models", []),
                    "last_seen": datetime.now().isoformat() if is_online else self._devices[ip].get("last_seen"),
                    "capabilities": {
                        "ollama": ollama["status"] == "online",
                        "agi_server": agi["status"] == "online",
                        "receiver": receiver["status"] == "online",
                        "models": ollama.get("models", [])
                    }
                })
                self._save_config()
                return self._devices[ip]

        return {
            "ip": ip,
            "status": "online" if is_online else "offline",
            "ollama_status": ollama["status"],
            "agi_status": agi["status"],
            "receiver_status": receiver["status"],
            "ollama_models": ollama.get("models", [])
        }

    def scan_lan(self, timeout=1.5, callback=None):
        """扫描局域网发现设备"""
        local_ip = self.get_local_ip()
        subnet = '.'.join(local_ip.split('.')[:3])
        found = []

        def scan_ip(ip):
            if ip == local_ip:
                return None
            # 检查Ollama端口或AGI端口
            has_ollama = self._check_port(ip, OLLAMA_PORT, timeout)
            has_agi = self._check_port(ip, AGI_PORT, timeout)
            has_receiver = self._check_port(ip, RECEIVER_PORT, timeout)
            if has_ollama or has_agi or has_receiver:
                return {
                    "ip": ip,
                    "has_ollama": has_ollama,
                    "has_agi": has_agi,
                    "has_receiver": has_receiver
                }
            return None

        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = {pool.submit(scan_ip, f"{subnet}.{i}"): i for i in range(1, 255)}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)
                    if callback:
                        callback(f"发现设备: {result['ip']}")

        # 对发现的设备获取详细信息
        for dev in found:
            ip = dev["ip"]
            if ip not in self._devices:
                # 自动添加发现的设备
                self.add_device(ip, name=f"Auto-{ip.split('.')[-1]}")
            self.probe_device(ip)

        return found

    def refresh_all(self):
        """刷新所有设备状态"""
        results = []
        for ip in list(self._devices.keys()):
            info = self.probe_device(ip)
            results.append(info)
        return results


# ==================== 一键迁移 ====================

class MigrationManager:
    """打包并迁移AGI系统到目标设备"""

    def __init__(self, device_manager):
        self.dm = device_manager
        self._progress = {}  # task_id -> progress info
        self._lock = threading.Lock()

    def _get_package_contents(self):
        """获取需要打包的文件列表"""
        contents = {
            "database": str(DB_PATH),
            "config_files": [],
            "workspace": str(WORKSPACE_DIR),
            "scripts": [],
            "web": str(BASE_DIR / "web"),
        }

        # 核心Python文件
        for f in BASE_DIR.glob("*.py"):
            if not f.name.startswith('_'):
                contents["scripts"].append(str(f))

        # 配置文件
        if CLUSTER_CONFIG.exists():
            contents["config_files"].append(str(CLUSTER_CONFIG))

        return contents

    def create_package(self, task_id, include_model_ref=True):
        """创建迁移包"""
        MIGRATE_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pkg_name = f"agi_migrate_{ts}"
        pkg_path = MIGRATE_DIR / f"{pkg_name}.zip"

        with self._lock:
            self._progress[task_id] = {
                "status": "packaging",
                "progress": 0,
                "message": "开始打包...",
                "package_path": str(pkg_path)
            }

        try:
            with zipfile.ZipFile(pkg_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 1. 数据库
                self._update_progress(task_id, 10, "打包数据库...")
                if DB_PATH.exists():
                    zf.write(DB_PATH, "memory.db")

                # 2. 核心脚本
                self._update_progress(task_id, 20, "打包核心脚本...")
                for f in BASE_DIR.glob("*.py"):
                    if not f.name.startswith('_'):
                        zf.write(f, f.name)

                # 3. Web前端
                self._update_progress(task_id, 35, "打包Web前端...")
                web_dir = BASE_DIR / "web"
                if web_dir.exists():
                    for f in web_dir.rglob("*"):
                        if f.is_file():
                            zf.write(f, f"web/{f.relative_to(web_dir)}")

                # 4. 工作区
                self._update_progress(task_id, 50, "打包工作区...")
                if WORKSPACE_DIR.exists():
                    for f in WORKSPACE_DIR.rglob("*"):
                        if f.is_file() and '__pycache__' not in str(f):
                            zf.write(f, f"workspace/{f.relative_to(WORKSPACE_DIR)}")

                # 5. 集群配置
                self._update_progress(task_id, 70, "打包配置...")
                if CLUSTER_CONFIG.exists():
                    zf.write(CLUSTER_CONFIG, "cluster_config.json")

                # 6. 模型引用清单（不打包模型本身，在目标机器用ollama pull）
                if include_model_ref:
                    self._update_progress(task_id, 80, "生成模型清单...")
                    model_manifest = self._get_model_manifest()
                    zf.writestr("model_manifest.json", json.dumps(model_manifest, ensure_ascii=False, indent=2))

                # 7. 迁移说明和自动安装脚本
                self._update_progress(task_id, 90, "生成安装脚本...")
                install_script = self._generate_install_script()
                zf.writestr("install.py", install_script)

                readme = self._generate_readme()
                zf.writestr("README.md", readme)

            pkg_size = pkg_path.stat().st_size
            self._update_progress(task_id, 100, f"打包完成: {pkg_size/1024/1024:.1f}MB")
            self._progress[task_id]["status"] = "packaged"
            self._progress[task_id]["size"] = pkg_size

            return {
                "success": True,
                "package": str(pkg_path),
                "size": pkg_size,
                "name": pkg_name
            }

        except Exception as e:
            self._update_progress(task_id, -1, f"打包失败: {e}")
            self._progress[task_id]["status"] = "error"
            return {"success": False, "error": str(e)}

    def _update_progress(self, task_id, progress, message):
        with self._lock:
            if task_id in self._progress:
                self._progress[task_id]["progress"] = progress
                self._progress[task_id]["message"] = message

    def get_progress(self, task_id):
        with self._lock:
            return self._progress.get(task_id, {"status": "unknown"})

    def _get_model_manifest(self):
        """获取当前Ollama模型清单"""
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", method='GET')
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            models = []
            for m in data.get('models', []):
                models.append({
                    "name": m.get("name", ""),
                    "size": m.get("size", 0),
                    "digest": m.get("digest", ""),
                    "modified_at": m.get("modified_at", "")
                })
            return {
                "models": models,
                "required": ["qwen2.5-coder:14b", "nomic-embed-text"],
                "source_os": platform.system(),
                "source_arch": platform.machine(),
                "exported_at": datetime.now().isoformat()
            }
        except Exception:
            return {
                "models": [],
                "required": ["qwen2.5-coder:14b", "nomic-embed-text"],
                "source_os": platform.system(),
                "exported_at": datetime.now().isoformat()
            }

    def _generate_install_script(self):
        """生成目标机器的自动安装脚本"""
        return '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 迁移安装脚本
在目标机器上运行此脚本完成部署
"""
import os, sys, json, subprocess, platform, shutil, zipfile
from pathlib import Path

def run(cmd, check=True):
    print(f"  > {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)

def main():
    print("=" * 50)
    print("  AGI v13.3 Cognitive Lattice — 迁移安装")
    print("=" * 50)

    target_dir = Path(os.environ.get("AGI_INSTALL_DIR", str(Path.home() / "AGI-实践器")))
    print(f"\\n安装目录: {target_dir}")

    # 1. 创建目录
    target_dir.mkdir(parents=True, exist_ok=True)

    # 2. 复制文件（假设在解压后的目录中运行）
    src = Path(__file__).parent
    print("\\n[1/5] 复制文件...")
    for item in src.iterdir():
        if item.name in ('install.py', 'README.md'):
            continue
        dst = target_dir / item.name
        if item.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(item, dst)
        else:
            shutil.copy2(item, dst)
    print(f"  ✓ 文件已复制到 {target_dir}")

    # 3. 创建虚拟环境
    print("\\n[2/5] 创建Python虚拟环境...")
    venv_dir = target_dir / "venv"
    if not venv_dir.exists():
        run(f"{sys.executable} -m venv {venv_dir}")
    pip = str(venv_dir / ("Scripts" if platform.system() == "Windows" else "bin") / "pip")
    run(f"{pip} install flask flask-cors openai numpy requests")
    print("  ✓ 依赖已安装")

    # 4. 安装Ollama模型
    print("\\n[3/5] 检查Ollama模型...")
    manifest_path = src / "model_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        for model in manifest.get("required", []):
            print(f"  拉取模型: {model}")
            result = run(f"ollama pull {model}", check=False)
            if result.returncode == 0:
                print(f"  ✓ {model} 就绪")
            else:
                print(f"  ⚠ {model} 拉取失败，请手动执行: ollama pull {model}")

    # 5. 验证
    print("\\n[4/5] 验证安装...")
    python = str(venv_dir / ("Scripts" if platform.system() == "Windows" else "bin") / "python")
    result = run(f"{python} -c \\"import flask; import openai; print(\'deps ok\');\\"", check=False)
    if "deps ok" in (result.stdout or ""):
        print("  ✓ 依赖验证通过")
    else:
        print("  ⚠ 部分依赖可能缺失")

    # 6. 生成启动脚本
    print("\\n[5/5] 生成启动脚本...")
    if platform.system() == "Windows":
        start_script = target_dir / "start.bat"
        start_script.write_text(f"@echo off\\ncd /d {target_dir}\\n{python} api_server.py\\npause\\n")
    else:
        start_script = target_dir / "start.sh"
        start_script.write_text(f"#!/bin/bash\\ncd {target_dir}\\n{python} api_server.py\\n")
        os.chmod(start_script, 0o755)

    print(f"\\n{'=' * 50}")
    print(f"  ✓ 安装完成!")
    print(f"  启动: {start_script}")
    print(f"  访问: http://localhost:5002")
    print(f"{'=' * 50}")

if __name__ == "__main__":
    main()
'''

    def _generate_readme(self):
        return """# AGI v13.3 Cognitive Lattice — 迁移包

## 快速安装

### macOS / Linux
```bash
unzip agi_migrate_*.zip -d agi_migrate
cd agi_migrate
python3 install.py
```

### Windows
```powershell
Expand-Archive agi_migrate_*.zip -DestinationPath agi_migrate
cd agi_migrate
python install.py
```

## 前置要求
1. Python 3.10+
2. Ollama 已安装并运行 (https://ollama.ai)
3. 足够的磁盘空间 (模型约 8-10GB)

## 手动安装
1. 解压到目标目录
2. 创建虚拟环境: `python3 -m venv venv`
3. 安装依赖: `pip install flask flask-cors openai numpy requests`
4. 拉取模型: `ollama pull qwen2.5-coder:14b && ollama pull nomic-embed-text`
5. 启动: `python api_server.py`
6. 访问: http://localhost:5002

## 分布式连接
在源机器的Web界面中添加本机IP即可建立集群连接。
"""

    def push_to_device(self, task_id, target_ip, target_port=RECEIVER_PORT):
        """推送迁移包到目标设备"""
        progress = self.get_progress(task_id)
        if progress.get("status") != "packaged":
            return {"success": False, "error": "请先创建迁移包"}

        pkg_path = progress.get("package_path")
        if not pkg_path or not Path(pkg_path).exists():
            return {"success": False, "error": "迁移包不存在"}

        self._update_progress(task_id, 0, f"推送到 {target_ip}...")
        self._progress[task_id]["status"] = "pushing"

        try:
            import urllib.request
            # 检查接收端是否就绪
            try:
                req = urllib.request.Request(f"http://{target_ip}:{target_port}/status")
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                return {"success": False, "error": f"目标设备 {target_ip}:{target_port} 接收端未启动，请先在目标机器运行 migrate_receiver.py"}

            # 分块推送
            pkg_size = Path(pkg_path).stat().st_size
            chunk_size = 1024 * 1024  # 1MB chunks

            with open(pkg_path, 'rb') as f:
                chunk_idx = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    # 发送chunk
                    req = urllib.request.Request(
                        f"http://{target_ip}:{target_port}/upload",
                        data=json.dumps({
                            "chunk_idx": chunk_idx,
                            "data": chunk.hex(),
                            "total_size": pkg_size,
                            "filename": Path(pkg_path).name
                        }).encode(),
                        headers={"Content-Type": "application/json"},
                        method='POST'
                    )
                    urllib.request.urlopen(req, timeout=30)
                    sent = min((chunk_idx + 1) * chunk_size, pkg_size)
                    pct = int(sent / pkg_size * 100)
                    self._update_progress(task_id, pct, f"推送中... {sent/1024/1024:.1f}/{pkg_size/1024/1024:.1f}MB")
                    chunk_idx += 1

            # 触发安装
            req = urllib.request.Request(
                f"http://{target_ip}:{target_port}/install",
                data=json.dumps({"filename": Path(pkg_path).name}).encode(),
                headers={"Content-Type": "application/json"},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read().decode())

            self._update_progress(task_id, 100, "迁移完成!")
            self._progress[task_id]["status"] = "completed"
            return {"success": True, "result": result}

        except Exception as e:
            self._update_progress(task_id, -1, f"推送失败: {e}")
            self._progress[task_id]["status"] = "error"
            return {"success": False, "error": str(e)}


# ==================== 分布式通讯 ====================

class DistributedRouter:
    """分布式推理路由器"""

    def __init__(self, device_manager):
        self.dm = device_manager
        self._active_devices = {}  # ip -> connection info
        self._routing_mode = "local"  # local | round_robin | load_balance | specific
        self._specific_device = None
        self._rr_index = 0
        self._lock = threading.Lock()

    def set_routing(self, mode, device_ip=None):
        """设置路由模式"""
        with self._lock:
            self._routing_mode = mode
            if mode == "specific" and device_ip:
                self._specific_device = device_ip
        return {"mode": mode, "device": device_ip}

    def get_routing(self):
        """获取当前路由配置"""
        return {
            "mode": self._routing_mode,
            "specific_device": self._specific_device,
            "active_devices": list(self._active_devices.keys())
        }

    def connect_device(self, ip):
        """连接设备用于分布式推理"""
        info = self.dm.probe_device(ip)
        if info.get("ollama_status") == "online":
            with self._lock:
                self._active_devices[ip] = {
                    "ip": ip,
                    "connected_at": datetime.now().isoformat(),
                    "models": info.get("ollama_models", []),
                    "request_count": 0,
                    "last_request": None
                }
            return {"success": True, "device": info}
        return {"success": False, "error": f"{ip} Ollama不可用"}

    def disconnect_device(self, ip):
        """断开设备"""
        with self._lock:
            if ip in self._active_devices:
                del self._active_devices[ip]
                if self._specific_device == ip:
                    self._specific_device = None
                    self._routing_mode = "local"
                return True
        return False

    def get_target_device(self):
        """根据路由策略获取目标设备"""
        with self._lock:
            if self._routing_mode == "local":
                return None  # 使用本地

            if self._routing_mode == "specific" and self._specific_device:
                if self._specific_device in self._active_devices:
                    return self._specific_device
                return None

            if self._routing_mode == "round_robin":
                ips = list(self._active_devices.keys())
                if not ips:
                    return None
                ip = ips[self._rr_index % len(ips)]
                self._rr_index += 1
                return ip

            return None

    def route_llm_call(self, messages, model="qwen2.5-coder:14b"):
        """路由LLM调用到目标设备"""
        target = self.get_target_device()
        if not target:
            return None  # 回退到本地

        try:
            import urllib.request
            payload = json.dumps({
                "model": model,
                "messages": messages,
                "stream": False
            }).encode()

            req = urllib.request.Request(
                f"http://{target}:{OLLAMA_PORT}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read().decode())

            with self._lock:
                if target in self._active_devices:
                    self._active_devices[target]["request_count"] += 1
                    self._active_devices[target]["last_request"] = datetime.now().isoformat()

            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"raw": content, "_routed_to": target}

        except Exception as e:
            return {"error": str(e), "_routed_to": target}


# ==================== 飞书 OpenClaw 集成 ====================

class FeishuIntegration:
    """飞书机器人集成"""

    def __init__(self, device_manager):
        self.dm = device_manager
        self._config = device_manager._feishu_config if hasattr(device_manager, '_feishu_config') else {}
        self._enabled = False
        self._webhook_url = self._config.get('webhook_url', '')
        self._app_id = self._config.get('app_id', '')
        self._app_secret = self._config.get('app_secret', '')
        self._openclaw_endpoint = self._config.get('openclaw_endpoint', '')
        self._lock = threading.Lock()

    def configure(self, webhook_url="", app_id="", app_secret="", openclaw_endpoint=""):
        """配置飞书集成"""
        with self._lock:
            if webhook_url:
                self._webhook_url = webhook_url
            if app_id:
                self._app_id = app_id
            if app_secret:
                self._app_secret = app_secret
            if openclaw_endpoint:
                self._openclaw_endpoint = openclaw_endpoint

            self._config = {
                "webhook_url": self._webhook_url,
                "app_id": self._app_id,
                "app_secret": self._app_secret,
                "openclaw_endpoint": self._openclaw_endpoint,
                "enabled": bool(self._webhook_url or self._openclaw_endpoint)
            }
            self._enabled = self._config["enabled"]

            # 保存到device_manager配置
            self.dm._feishu_config = self._config
            self.dm._save_config()

        return self.get_config()

    def get_config(self):
        """获取当前配置（隐藏敏感信息）"""
        return {
            "webhook_url": self._webhook_url[:20] + "..." if len(self._webhook_url) > 20 else self._webhook_url,
            "app_id": self._app_id[:8] + "..." if len(self._app_id) > 8 else self._app_id,
            "has_secret": bool(self._app_secret),
            "openclaw_endpoint": self._openclaw_endpoint,
            "enabled": self._enabled
        }

    def send_message(self, text, msg_type="text"):
        """通过Webhook发送消息到飞书"""
        if not self._webhook_url:
            return {"success": False, "error": "未配置飞书Webhook URL"}

        try:
            import urllib.request
            if msg_type == "text":
                payload = json.dumps({
                    "msg_type": "text",
                    "content": {"text": text}
                }).encode()
            elif msg_type == "interactive":
                payload = json.dumps({
                    "msg_type": "interactive",
                    "card": {
                        "header": {
                            "title": {"tag": "plain_text", "content": "AGI Cognitive Lattice"},
                            "template": "purple"
                        },
                        "elements": [
                            {"tag": "markdown", "content": text}
                        ]
                    }
                }).encode()
            else:
                payload = json.dumps({
                    "msg_type": "text",
                    "content": {"text": text}
                }).encode()

            req = urllib.request.Request(
                self._webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            return {"success": result.get("code", -1) == 0 or result.get("StatusCode", -1) == 0,
                    "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_card(self, title, content, buttons=None):
        """发送卡片消息"""
        if not self._webhook_url:
            return {"success": False, "error": "未配置飞书Webhook URL"}

        elements = [{"tag": "markdown", "content": content}]
        if buttons:
            actions = []
            for btn in buttons:
                actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": btn.get("text", "按钮")},
                    "type": btn.get("type", "primary"),
                    "value": btn.get("value", {})
                })
            elements.append({"tag": "action", "actions": actions})

        return self.send_message(json.dumps({
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "purple"
                },
                "elements": elements
            }
        }), msg_type="raw")

    def forward_to_openclaw(self, message, session_id=""):
        """通过OpenClaw转发消息"""
        if not self._openclaw_endpoint:
            return {"success": False, "error": "未配置OpenClaw端点"}

        try:
            import urllib.request
            payload = json.dumps({
                "message": message,
                "session_id": session_id,
                "source": "agi_cognitive_lattice",
                "timestamp": datetime.now().isoformat()
            }).encode()

            req = urllib.request.Request(
                self._openclaw_endpoint,
                data=payload,
                headers={"Content-Type": "application/json"},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode())
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_incoming(self, data):
        """处理从飞书/OpenClaw收到的消息"""
        # 验证请求
        event_type = data.get("type", "")

        # 飞书URL验证
        if event_type == "url_verification":
            return {"challenge": data.get("challenge", "")}

        # 提取消息内容
        event = data.get("event", {})
        message = event.get("message", {})
        content = message.get("content", "")
        sender = event.get("sender", {}).get("sender_id", {}).get("user_id", "unknown")

        if content:
            try:
                content_obj = json.loads(content)
                text = content_obj.get("text", "")
            except (json.JSONDecodeError, TypeError):
                text = str(content)
        else:
            text = ""

        return {
            "text": text,
            "sender": sender,
            "message_id": message.get("message_id", ""),
            "chat_id": message.get("chat_id", "")
        }


# ==================== 全局实例 ====================

_device_manager = None
_migration_manager = None
_distributed_router = None
_feishu_integration = None


def get_device_manager():
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager


def get_migration_manager():
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager(get_device_manager())
    return _migration_manager


def get_distributed_router():
    global _distributed_router
    if _distributed_router is None:
        _distributed_router = DistributedRouter(get_device_manager())
    return _distributed_router


def get_feishu_integration():
    global _feishu_integration
    if _feishu_integration is None:
        _feishu_integration = FeishuIntegration(get_device_manager())
    return _feishu_integration
