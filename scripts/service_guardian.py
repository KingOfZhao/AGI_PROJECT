#!/usr/bin/env python3
"""
服务守护进程 - 自动监控并重启崩溃的服务
除非收到明确停止命令，否则持续守护

用法:
  python3 scripts/service_guardian.py              # 启动守护
  python3 scripts/service_guardian.py --stop       # 优雅停止所有服务
  python3 scripts/service_guardian.py --status     # 查看状态
  python3 scripts/service_guardian.py --restart    # 重启所有服务
"""

import os
import sys
import time
import json
import signal
import socket
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable

PROJECT_ROOT = Path(__file__).parent.parent
GUARDIAN_PID_FILE = PROJECT_ROOT / ".guardian.pid"
GUARDIAN_STATE_FILE = PROJECT_ROOT / ".guardian_state.json"
LOG_FILE = PROJECT_ROOT / "logs" / "guardian.log"

# 确保日志目录存在
LOG_FILE.parent.mkdir(exist_ok=True)


class ServiceConfig:
    """服务配置"""
    def __init__(
        self,
        name: str,
        port: int,
        start_cmd: List[str],
        cwd: Optional[Path] = None,
        health_check: Optional[Callable] = None,
        restart_delay: int = 3,
        max_restarts: int = 10,
        restart_window: int = 300,  # 5分钟内最多重启次数
    ):
        self.name = name
        self.port = port
        self.start_cmd = start_cmd
        self.cwd = cwd or PROJECT_ROOT
        self.health_check = health_check or (lambda: self._default_health_check())
        self.restart_delay = restart_delay
        self.max_restarts = max_restarts
        self.restart_window = restart_window
        
        # 运行时状态
        self.process: Optional[subprocess.Popen] = None
        self.restart_times: List[float] = []
        self.status = "stopped"
        self.last_error = ""
    
    def _default_health_check(self) -> bool:
        """默认健康检查：端口是否可达"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', self.port))
            sock.close()
            return result == 0
        except:
            return False


def log(msg: str, level: str = "INFO"):
    """写日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


class ServiceGuardian:
    """服务守护进程"""
    
    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.running = False
        self.check_interval = 10  # 每10秒检查一次
        self._setup_services()
    
    def _setup_services(self):
        """配置需要守护的服务"""
        python = sys.executable
        
        # OpenClaw Bridge (核心服务)
        self.services["bridge"] = ServiceConfig(
            name="OpenClaw Bridge",
            port=9801,
            start_cmd=[python, "scripts/openclaw_bridge.py"],
            restart_delay=5,
        )
        
        # CRM 系统 (静态文件服务)
        self.services["crm"] = ServiceConfig(
            name="CRM System",
            port=8890,
            start_cmd=[python, "-m", "http.server", "8890", "--directory", "web"],
            restart_delay=2,
        )
        
        # API 服务器 (如果存在)
        api_server = PROJECT_ROOT / "api" / "api_server.py"
        if api_server.exists():
            self.services["api"] = ServiceConfig(
                name="API Server",
                port=8080,
                start_cmd=[python, "api/api_server.py"],
                restart_delay=3,
            )
        
        # WeChat Gateway (如果配置存在)
        wechat_gateway = PROJECT_ROOT / "scripts" / "wechat_gateway.py"
        if wechat_gateway.exists():
            self.services["wechat"] = ServiceConfig(
                name="WeChat Gateway",
                port=5000,
                start_cmd=[python, "scripts/wechat_gateway.py"],
                restart_delay=5,
            )
        
        # 闲置推演引擎 (无端口，通过PID文件检测)
        idle_growth = PROJECT_ROOT / "scripts" / "idle_growth_engine.py"
        if idle_growth.exists():
            def idle_health_check():
                pid_file = PROJECT_ROOT / ".idle_growth.pid"
                if not pid_file.exists():
                    return False
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, 0)
                    return True
                except:
                    return False
            
            self.services["idle_growth"] = ServiceConfig(
                name="Idle Growth Engine",
                port=0,  # 无端口
                start_cmd=[python, "scripts/idle_growth_engine.py"],
                health_check=idle_health_check,
                restart_delay=10,
            )
    
    def start_service(self, name: str) -> bool:
        """启动单个服务"""
        if name not in self.services:
            log(f"未知服务: {name}", "ERROR")
            return False
        
        svc = self.services[name]
        
        # 检查是否已经在运行
        if svc.health_check():
            log(f"[{svc.name}] 已在运行 (port {svc.port})")
            svc.status = "running"
            return True
        
        # 检查重启次数限制
        now = time.time()
        svc.restart_times = [t for t in svc.restart_times if now - t < svc.restart_window]
        if len(svc.restart_times) >= svc.max_restarts:
            log(f"[{svc.name}] 重启次数过多 ({len(svc.restart_times)}/{svc.max_restarts} in {svc.restart_window}s), 暂停守护", "ERROR")
            svc.status = "failed"
            svc.last_error = "重启次数超限"
            return False
        
        # 启动服务
        try:
            log(f"[{svc.name}] 启动中... (port {svc.port})")
            svc.process = subprocess.Popen(
                svc.start_cmd,
                cwd=str(svc.cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            svc.restart_times.append(now)
            
            # 等待启动
            time.sleep(svc.restart_delay)
            
            if svc.health_check():
                log(f"[{svc.name}] ✅ 启动成功 (PID {svc.process.pid})")
                svc.status = "running"
                return True
            else:
                log(f"[{svc.name}] ⚠️ 启动后健康检查失败", "WARN")
                svc.status = "unhealthy"
                return False
                
        except Exception as e:
            log(f"[{svc.name}] ❌ 启动失败: {e}", "ERROR")
            svc.status = "failed"
            svc.last_error = str(e)
            return False
    
    def stop_service(self, name: str) -> bool:
        """停止单个服务"""
        if name not in self.services:
            return False
        
        svc = self.services[name]
        
        # 通过端口查找进程
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{svc.port}"],
                capture_output=True,
                text=True,
            )
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    os.kill(int(pid), signal.SIGTERM)
                    log(f"[{svc.name}] 已停止 (PID {pid})")
        except:
            pass
        
        if svc.process:
            try:
                svc.process.terminate()
                svc.process.wait(timeout=5)
            except:
                try:
                    svc.process.kill()
                except:
                    pass
        
        svc.process = None
        svc.status = "stopped"
        return True
    
    def check_and_restart(self):
        """检查所有服务，必要时重启"""
        for name, svc in self.services.items():
            if svc.status == "failed":
                continue  # 已失败的服务不再尝试
            
            if not svc.health_check():
                log(f"[{svc.name}] ❌ 健康检查失败，尝试重启...")
                svc.status = "restarting"
                self.start_service(name)
    
    def run(self):
        """主守护循环"""
        # 写入 PID 文件
        with open(GUARDIAN_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        
        self.running = True
        log("=" * 50)
        log("🛡️ 服务守护进程启动")
        log(f"守护服务: {', '.join(self.services.keys())}")
        log(f"检查间隔: {self.check_interval}s")
        log("=" * 50)
        
        # 注册信号处理
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        
        # 首次启动所有服务
        for name in self.services:
            self.start_service(name)
        
        # 守护循环
        while self.running:
            try:
                time.sleep(self.check_interval)
                self.check_and_restart()
                self._save_state()
            except Exception as e:
                log(f"守护循环异常: {e}", "ERROR")
        
        log("🛡️ 守护进程已退出")
    
    def _handle_signal(self, signum, frame):
        """处理停止信号"""
        log(f"收到信号 {signum}, 准备退出...")
        self.running = False
    
    def _save_state(self):
        """保存状态到文件"""
        state = {
            "pid": os.getpid(),
            "updated": datetime.now().isoformat(),
            "services": {
                name: {
                    "name": svc.name,
                    "port": svc.port,
                    "status": svc.status,
                    "restarts": len(svc.restart_times),
                    "last_error": svc.last_error,
                }
                for name, svc in self.services.items()
            }
        }
        with open(GUARDIAN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def stop_all(self):
        """停止所有服务"""
        log("正在停止所有服务...")
        for name in self.services:
            self.stop_service(name)
        
        # 清理 PID 文件
        if GUARDIAN_PID_FILE.exists():
            GUARDIAN_PID_FILE.unlink()
        
        log("所有服务已停止")


def get_status() -> dict:
    """获取守护状态"""
    if not GUARDIAN_STATE_FILE.exists():
        return {"running": False, "services": {}}
    
    try:
        with open(GUARDIAN_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        # 检查守护进程是否还在运行
        if GUARDIAN_PID_FILE.exists():
            pid = int(GUARDIAN_PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                state["running"] = True
            except:
                state["running"] = False
        else:
            state["running"] = False
        
        return state
    except:
        return {"running": False, "services": {}}


def stop_guardian():
    """停止守护进程"""
    if not GUARDIAN_PID_FILE.exists():
        print("守护进程未运行")
        return
    
    try:
        pid = int(GUARDIAN_PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"已发送停止信号到守护进程 (PID {pid})")
        
        # 等待进程退出
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("守护进程已退出")
                return
        
        print("守护进程未响应，强制终止...")
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        print("守护进程已不存在")
        GUARDIAN_PID_FILE.unlink()
    except Exception as e:
        print(f"停止失败: {e}")


def print_status():
    """打印状态"""
    state = get_status()
    
    print("\n" + "=" * 50)
    print("🛡️ AGI 服务守护状态")
    print("=" * 50)
    
    if state.get("running"):
        print(f"守护进程: ✅ 运行中 (PID {state.get('pid', '?')})")
    else:
        print("守护进程: ❌ 未运行")
    
    print(f"更新时间: {state.get('updated', '-')}")
    print("-" * 50)
    
    services = state.get("services", {})
    if not services:
        print("无服务信息")
    else:
        for key, svc in services.items():
            status_icon = {
                "running": "✅",
                "stopped": "⬜",
                "failed": "❌",
                "restarting": "🔄",
                "unhealthy": "⚠️",
            }.get(svc.get("status", ""), "❓")
            
            print(f"  {status_icon} {svc['name']:<20} port:{svc['port']:<6} restarts:{svc.get('restarts', 0)}")
            if svc.get("last_error"):
                print(f"      └─ {svc['last_error']}")
    
    print("=" * 50 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AGI 服务守护进程")
    parser.add_argument("--stop", action="store_true", help="停止守护进程和所有服务")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--restart", action="store_true", help="重启所有服务")
    parser.add_argument("--daemon", "-d", action="store_true", help="后台运行")
    args = parser.parse_args()
    
    if args.status:
        print_status()
        return
    
    if args.stop:
        stop_guardian()
        guardian = ServiceGuardian()
        guardian.stop_all()
        return
    
    if args.restart:
        stop_guardian()
        guardian = ServiceGuardian()
        guardian.stop_all()
        time.sleep(2)
    
    # 检查是否已有守护进程
    if GUARDIAN_PID_FILE.exists():
        try:
            pid = int(GUARDIAN_PID_FILE.read_text().strip())
            os.kill(pid, 0)
            print(f"守护进程已在运行 (PID {pid})")
            print("使用 --stop 停止，或 --restart 重启")
            return
        except ProcessLookupError:
            GUARDIAN_PID_FILE.unlink()
    
    # 后台运行
    if args.daemon:
        if os.fork() > 0:
            print("守护进程已启动（后台）")
            return
        os.setsid()
        if os.fork() > 0:
            sys.exit(0)
    
    # 启动守护
    guardian = ServiceGuardian()
    guardian.run()


if __name__ == "__main__":
    main()
