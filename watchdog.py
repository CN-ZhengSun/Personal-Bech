# -*- coding: utf-8 -*-
"""测试工作台守护进程：每 20 秒检测后端(8000)/前端(5173)，挂了自动拉起。
单实例保护：绑定本地 8755 端口作为互斥锁，保证全系统只有一个 watchdog 实例。"""
import socket
import subprocess
import time
import os
import urllib.request

BACKEND = r"D:\Test-Bench\backend\.venv\Scripts\python.exe"
BACKEND_DIR = r"D:\Test-Bench\backend"
FRONTEND_DIR = r"D:\Test-Bench\frontend"
LOG_DIR = r"D:\Test-Bench\logs"
START_SCRIPT = r"D:\Test-Bench\start-services.ps1"
os.makedirs(LOG_DIR, exist_ok=True)

_LOCK_PORT = 8755
_lock_sock = None


def acquire_lock():
    """绑定本地端口作为互斥锁；成功返回 True，失败说明已有实例。"""
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 注意：Windows 上不能设置 SO_REUSEADDR（允许重复绑定导致锁失效），默认独占绑定
    try:
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        _lock_sock = s
        return True
    except OSError:
        try:
            s.close()
        except OSError:
            pass
        return False


def port_open(port):
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def backend_healthy():
    """确认后端不仅占用端口，而且能完成一次真实请求。"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as response:
            return response.status == 200
    except (OSError, TimeoutError):
        return False


def recover_backend():
    """交给启动脚本校验并只清理本项目的异常后端进程。"""
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", START_SCRIPT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )


_last_start = {"backend": 0.0, "frontend": 0.0}
COOLDOWN = 30  # 秒：同一服务在冷却期内不重复拉起，防止 uvicorn/vite 启动慢时被重复启动


def _cooldown_ok(key: str) -> bool:
    now = time.time()
    if now - _last_start[key] < COOLDOWN:
        return False
    _last_start[key] = now
    return True


def start_backend():
    if not _cooldown_ok("backend"):
        return
    with open(os.path.join(LOG_DIR, "backend.log"), "a", encoding="utf-8") as f:
        subprocess.Popen(
            [BACKEND, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=BACKEND_DIR,
            stdout=f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def start_frontend():
    if not _cooldown_ok("frontend"):
        return
    # 只由外层句柄写 frontend.log，cmd 内不再重定向，避免 Windows 文件锁冲突
    with open(os.path.join(LOG_DIR, "frontend.log"), "a", encoding="utf-8") as f:
        subprocess.Popen(
            ["cmd.exe", "/c", "npm run dev"],
            cwd=FRONTEND_DIR,
            stdout=f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def log(msg: str):
    """watchdog 自身日志，用于追溯守护进程状态与异常。"""
    try:
        with open(os.path.join(LOG_DIR, "watchdog.log"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    if not acquire_lock():
        log("检测到已有 watchdog 实例运行，本实例退出")
        raise SystemExit(0)
    log("watchdog 启动")
    while True:
        try:
            if not backend_healthy():
                if port_open(8000):
                    log("检测到后端无响应，执行受限恢复")
                    recover_backend()
                else:
                    log("检测到 8000 DOWN，拉起后端")
                    start_backend()
            if not port_open(5173):
                log("检测到 5173 DOWN，拉起前端")
                start_frontend()
        except Exception as e:  # noqa: BLE001
            # 任何异常都不能让守护进程退出，记录后继续下一轮检查
            log(f"主循环异常（已忽略继续运行）: {e!r}")
        time.sleep(20)
