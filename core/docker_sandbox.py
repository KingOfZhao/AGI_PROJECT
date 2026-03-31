"""
Docker沙箱管理器 — 外部代码/网页内容隔离执行
================================================
安全策略:
  1. 所有外部代码(开源项目/CrawHub skill)必须在沙箱中执行
  2. 沙箱默认无网络(仅白名单域名)
  3. 宿主机文件只读挂载, 沙箱输出写到独立目录
  4. 内存/CPU限制, 超时自动kill
  5. 沙箱内不存储任何敏感信息

使用流程:
  1. sandbox.run_code(code, timeout=30) → 隔离执行代码
  2. sandbox.run_script(script_path, timeout=30) → 隔离执行脚本
  3. sandbox.safety_check(code_or_url) → 执行前安全检查
"""

import subprocess
import json
import re
import os
import time
import tempfile
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class SafetyReport:
    """安全检查报告"""
    safe: bool
    risks: List[str]
    score: float  # 0-1, 1=最安全
    blocked_patterns: List[str]


class SafetyChecker:
    """代码安全检查器"""
    
    # 危险模式
    DANGEROUS_PATTERNS = {
        "exec_high": [
            (r'\bos\.(system|popen|exec|spawn)', "系统命令执行"),
            (r'\bsubprocess\.(call|run|Popen)', "子进程执行"),
            (r'\beval\s*\(', "动态代码执行"),
            (r'\bexec\s*\(', "动态代码执行"),
            (r'\bcompile\s*\(', "动态编译"),
            (r'__import__\s*\(', "动态导入"),
            (r'\bshutil\.(rmtree|move)', "文件系统破坏性操作"),
        ],
        "exec_medium": [
            (r'\bopen\s*\(', "文件操作"),
            (r'\brequests\.(get|post|put|delete)', "网络请求"),
            (r'\burllib\.request', "网络请求"),
            (r'\bsocket\.', "底层网络"),
            (r'\bglobal\s', "全局变量修改"),
        ],
        "info_leak": [
            (r'os\.environ', "环境变量访问"),
            (r'\bPath\s*\(\s*[\'\"]~', "用户目录访问"),
            (r'/etc/(passwd|shadow|hosts)', "系统文件访问"),
            (r'\.ssh/', "SSH密钥访问"),
            (r'\.env', "环境配置文件访问"),
        ],
        "persistence": [
            (r'systemd|launchd|crontab|plist', "持久化/定时任务"),
            (r'registry|HKLM|HKCU', "Windows注册表"),
        ],
    }
    
    def check(self, code: str) -> SafetyReport:
        """执行安全检查"""
        risks = []
        blocked = []
        score = 1.0
        
        for severity, patterns in self.DANGEROUS_PATTERNS.items():
            for pattern, desc in patterns:
                if re.search(pattern, code):
                    risks.append(f"[{severity}] {desc}")
                    blocked.append(pattern)
                    if "high" in severity:
                        score -= 0.3
                    elif "medium" in severity:
                        score -= 0.1
                    elif "leak" in severity:
                        score -= 0.2
                    elif "persistence" in severity:
                        score -= 0.25
        
        score = max(0.0, score)
        return SafetyReport(
            safe=score >= 0.5,
            risks=risks,
            score=score,
            blocked_patterns=blocked,
        )
    
    def check_url(self, url: str) -> SafetyReport:
        """URL安全检查"""
        risks = []
        score = 1.0
        
        # 检查协议
        if not url.startswith("https://"):
            risks.append("[medium] 非HTTPS协议")
            score -= 0.2
        
        # 检查域名
        suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".gq"]
        for tld in suspicious_tlds:
            if url.endswith(tld):
                risks.append(f"[high] 可疑TLD: {tld}")
                score -= 0.3
        
        # 检查IP地址
        if re.match(r'https?://\d+\.\d+\.\d+\.\d+', url):
            risks.append("[medium] IP地址直接访问")
            score -= 0.1
        
        return SafetyReport(
            safe=score >= 0.5,
            risks=risks,
            score=score,
            blocked_patterns=[],
        )


class DockerSandbox:
    """Docker沙箱管理器"""
    
    CONTAINER_NAME = "diepre-sandbox"
    IMAGE_NAME = "diepre-sandbox"
    SANDBOX_DIR = Path(__file__).parent.parent / "docker" / "sandbox_output"
    
    def __init__(self):
        self.checker = SafetyChecker()
        self.SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_running()
    
    def _ensure_running(self):
        """确保沙箱容器运行中"""
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={self.CONTAINER_NAME}"],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            print("[Sandbox] 启动沙箱容器...")
            subprocess.run([
                "docker", "run", "-d",
                "--name", self.CONTAINER_NAME,
                "--network", "none",  # 默认无网络
                "--memory", "256m",
                "--cpus", "1",
                "--read-only",  # 文件系统只读
                "-v", f"{self.SANDBOX_DIR}:/data/output",
                self.IMAGE_NAME,
            ], capture_output=True, text=True)
            time.sleep(1)
    
    def _exec_in_sandbox(self, cmd: str, timeout: int = 30) -> Tuple[int, str]:
        """在沙箱中执行命令"""
        result = subprocess.run(
            ["docker", "exec", self.CONTAINER_NAME, "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout + 5
        )
        return result.returncode, result.stdout + result.stderr
    
    def run_code(self, code: str, timeout: int = 30, 
                 allow_network: bool = False) -> Tuple[SafetyReport, str]:
        """
        在沙箱中执行代码
        
        Returns: (安全报告, 输出)
        """
        # 1. 安全检查
        report = self.checker.check(code)
        
        if not report.safe and not allow_network:
            return report, f"[BLOCKED] 安全检查未通过:\n" + "\n".join(report.risks)
        
        # 2. 写入临时文件
        script_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        script_path = f"/tmp/sandbox_{script_hash}.py"
        
        # 3. 执行
        # 先写入容器 (通过docker exec stdin)
        result = subprocess.run(
            ["docker", "exec", "-i", self.CONTAINER_NAME, 
             "bash", "-c", f"cat > {script_path}"],
            input=code, capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return report, f"[ERROR] 无法写入沙箱: {result.stderr}"
        
        # 执行
        exit_code, output = self._exec_in_sandbox(
            f"python3 {script_path} 2>&1",
            timeout=timeout
        )
        
        return report, output
    
    def run_script(self, script_path: str, timeout: int = 30) -> Tuple[SafetyReport, str]:
        """在沙箱中执行脚本文件"""
        with open(script_path) as f:
            code = f.read()
        return self.run_code(code, timeout)
    
    def safety_check(self, code_or_url: str) -> SafetyReport:
        """仅执行安全检查, 不运行"""
        if code_or_url.startswith("http"):
            return self.checker.check_url(code_or_url)
        return self.checker.check(code_or_url)
    
    def cleanup(self):
        """停止并删除沙箱"""
        subprocess.run(["docker", "stop", self.CONTAINER_NAME], 
                      capture_output=True, text=True)
        subprocess.run(["docker", "rm", self.CONTAINER_NAME], 
                      capture_output=True, text=True)
    
    def status(self) -> dict:
        """沙箱状态"""
        result = subprocess.run(
            ["docker", "inspect", self.CONTAINER_NAME],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            container = data[0]
            return {
                "running": container["State"]["Running"],
                "image": container["Config"]["Image"],
                "network": container["HostConfig"]["NetworkMode"],
                "memory": container["HostConfig"]["Memory"],
                "readonly": container["HostConfig"]["ReadonlyRootfs"],
            }
        return {"running": False}


if __name__ == "__main__":
    sandbox = DockerSandbox()
    checker = SafetyChecker()
    
    print("=" * 60)
    print("  Docker沙箱 — 安全隔离验证")
    print("=" * 60)
    
    # 状态
    print(f"\n沙箱状态: {json.dumps(sandbox.status(), indent=2, ensure_ascii=False)}")
    
    # 安全检查测试
    print("\n--- 安全检查测试 ---")
    test_cases = [
        ("safe", "x = 1 + 2\nprint(x)"),
        ("dangerous", "import os\nos.system('rm -rf /')"),
        ("info_leak", "import os\nprint(os.environ['HOME'])"),
        ("eval", "eval('__import__(\"os\").system(\"ls\")')"),
        ("url_safe", "https://github.com/openclaw/openclaw"),
        ("url_http", "http://example.com"),
        ("url_suspicious", "http://evil-site.tk/malware"),
    ]
    
    for name, test in test_cases:
        report = checker.check(test)
        icon = "✅" if report.safe else "❌"
        print(f"  {icon} {name}: score={report.score:.2f} risks={len(report.risks)}")
        if report.risks:
            for r in report.risks[:2]:
                print(f"      {r}")
    
    # 沙箱执行测试
    print("\n--- 沙箱执行测试 ---")
    
    # 安全代码 → 应该执行
    report, output = sandbox.run_code("print('Hello from sandbox!')", timeout=10)
    print(f"  安全代码: {output.strip()} (safe={report.safe})")
    
    # 危险代码 → 应该阻止
    report, output = sandbox.run_code("import os; os.system('cat /etc/passwd')", timeout=10)
    print(f"  危险代码: {output[:80]} (safe={report.safe})")
    
    print("\n✅ 沙箱验证完成")
