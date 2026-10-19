# -*- coding: utf-8 -*-
"""ADB 工具集：设备管理 / 应用操作 / 截图录屏 / logcat 实时流。
第一批：设备列表与属性、无线连接、应用安装卸载清数据启动、当前Activity、截图、shell。
与埋点监控(tracking)共用系统 adb，命令串行执行避免冲突。
"""
import re
import sys
import json
import subprocess
import threading
import tempfile
import shutil
import os
import time
import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException, Body, Depends
from app.core.database import get_db
from app.core.security import get_current_user, get_current_websocket_user
from app.services.logcat import build_log_record, parse_package_uid_output, parse_process_output
from fastapi.responses import Response, FileResponse

router = APIRouter(prefix="/adb", tags=["adb-tools"], dependencies=[Depends(get_current_user)])
ws_router = APIRouter(prefix="/ws/adb", tags=["adb-tools-ws"], dependencies=[Depends(get_current_websocket_user)])

_SERIAL_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_PKG_RE = re.compile(r"^[A-Za-z0-9_.]+$")
_lock = threading.Lock()
_record_procs: dict[str, dict] = {}  # serial -> {proc, outfile}


def _valid_serial(serial: str) -> bool:
    return bool(serial and _SERIAL_RE.match(serial))


def _run(args, timeout=15, **kw):
    with _lock:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", **kw,
        )


def _load_process_map(serial: str) -> dict[str, str]:
    result = _run(["adb", "-s", serial, "shell", "ps", "-A"], timeout=10)
    return parse_process_output(result.stdout or "")


def _load_package_uid_map(serial: str) -> dict[str, tuple[str, ...]]:
    result = _run(
        ["adb", "-s", serial, "shell", "cmd", "package", "list", "packages", "-U"],
        timeout=15,
    )
    return parse_package_uid_output(result.stdout or "")


def _list_devices():
    r = _run(["adb", "devices", "-l"], timeout=8)
    devices = []
    for ln in r.stdout.splitlines()[1:]:
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split()
        serial, state = parts[0], parts[1]
        info = {}
        for p in parts[2:]:
            if ":" in p:
                k, _, v = p.partition(":")
                info[k] = v
        devices.append({"serial": serial, "state": state, **info})
    return devices


def _device_props(serial: str) -> dict:
    props = {}
    for key, prop in [
        ("model", "ro.product.model"),
        ("brand", "ro.product.brand"),
        ("version", "ro.build.version.release"),
        ("sdk", "ro.build.version.sdk"),
        ("abi", "ro.product.cpu.abi"),
    ]:
        r = _run(["adb", "-s", serial, "shell", "getprop", prop], timeout=8)
        props[key] = r.stdout.strip() if r.returncode == 0 else ""
    r = _run(["adb", "-s", serial, "shell", "wm", "size"], timeout=8)
    m = re.search(r"(\d+)x(\d+)", r.stdout or "")
    props["resolution"] = f"{m.group(1)}x{m.group(2)}" if m else ""
    return props


@router.get("/devices")
def adb_devices():
    """ADB 可用性 + 设备列表（含属性）。"""
    try:
        installed = True
        devs = _list_devices()
    except FileNotFoundError:
        return {"adb_installed": False, "devices": [], "error": "未检测到 adb，请安装 Android SDK platform-tools"}
    except Exception as e:  # noqa: BLE001
        return {"adb_installed": True, "devices": [], "error": str(e)}
    out = []
    for d in devs:
        item = dict(d)
        if d["state"] == "device":
            try:
                item.update(_device_props(d["serial"]))
            except Exception:  # noqa: BLE001
                pass
        out.append(item)
    return {"adb_installed": installed, "devices": out}


@router.post("/connect")
def adb_connect(host: str, port: int = 5555):
    """无线连接 adb connect host:port。"""
    if not host:
        raise HTTPException(400, "请填写设备 IP")
    target = f"{host}:{port}"
    r = _run(["adb", "connect", target], timeout=12)
    return {"ok": True, "output": (r.stdout + r.stderr).strip() or "connected"}


@router.post("/disconnect")
def adb_disconnect(serial: str = ""):
    """断开设备（空串断开全部）。"""
    if serial and not _valid_serial(serial):
        raise HTTPException(400, "非法设备序列号")
    args = ["adb", "disconnect"] + ([serial] if serial else [])
    r = _run(args, timeout=10)
    return {"ok": True, "output": (r.stdout + r.stderr).strip()}


def _require_device(serial: str):
    if not _valid_serial(serial):
        raise HTTPException(400, "非法设备序列号")
    devs = {d["serial"]: d["state"] for d in _list_devices()}
    state = devs.get(serial)
    if state is None:
        raise HTTPException(404, f"设备 {serial} 不在线")
    if state != "device":
        raise HTTPException(400, f"设备 {serial} 状态为 {state}，请在手机上允许 USB 调试授权")


@router.get("/devices/{serial}/info")
def device_info(serial: str):
    _require_device(serial)
    return {"serial": serial, **_device_props(serial)}


@router.get("/devices/{serial}/apps")
def device_apps(serial: str):
    """第三方应用列表（包名 + 应用名）。"""
    _require_device(serial)
    r = _run(["adb", "-s", serial, "shell", "pm", "list", "packages", "-3"], timeout=20)
    pkgs = sorted(
        ln.replace("package:", "").strip()
        for ln in (r.stdout or "").splitlines()
        if ln.strip().startswith("package:")
    )
    return {"packages": pkgs}


@router.post("/devices/{serial}/apk/package-name")
def device_apk_package_name(serial: str, file: UploadFile = File(...)):
    """上传 APK 并用本机 aapt2/aapt 解析包名（对应原项目 分析包名）。"""
    _require_device(serial)
    name = file.filename or "app.apk"
    tmp = os.path.join(tempfile.gettempdir(), f"twb_apk_{int(time.time()*1000)}_{name}")
    with open(tmp, "wb") as f:
        f.write(file.file.read())
    try:
        aapt2 = _find_aapt2()
        if aapt2:
            r = subprocess.run([aapt2, "dump", "packagename", tmp], capture_output=True,
                               text=True, timeout=30, encoding="utf-8", errors="replace")
            pkg = r.stdout.strip()
            if pkg and re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$", pkg):
                return {"packageName": pkg, "tool": "aapt2"}
        aapt = _find_aapt()
        if aapt:
            r = subprocess.run([aapt, "dump", "badging", tmp], capture_output=True,
                               text=True, timeout=30, encoding="utf-8", errors="replace")
            m = re.search(r"^package:\s+name='([^']+)'", r.stdout, re.M)
            if m:
                return {"packageName": m.group(1), "tool": "aapt"}
        raise HTTPException(422, "未能读取 APK 包名；请确认本机已安装 Android SDK build-tools")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _find_aapt2():
    """定位本机 aapt2 / aapt（Android SDK build-tools）。"""
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
             r"D:\Android\Sdk", r"D:\android-sdk-windows\android-sdk-windows"]
    for root in roots:
        if not root:
            continue
        bt = os.path.join(root, "build-tools")
        try:
            if os.path.isdir(bt):
                for ver in sorted(os.listdir(bt), reverse=True):
                    aapt2 = os.path.join(bt, ver, "aapt2.exe")
                    if os.path.exists(aapt2):
                        return aapt2
        except OSError:
            continue
    return None


def _find_aapt():
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
             r"D:\Android\Sdk", r"D:\android-sdk-windows\android-sdk-windows"]
    for root in roots:
        if not root:
            continue
        bt = os.path.join(root, "build-tools")
        try:
            if os.path.isdir(bt):
                for ver in sorted(os.listdir(bt), reverse=True):
                    aapt = os.path.join(bt, ver, "aapt.exe")
                    if os.path.exists(aapt):
                        return aapt
        except OSError:
            continue
    return None


@router.post("/devices/{serial}/install")
def device_install(serial: str, file: UploadFile = File(...), flag: str = "-r"):
    """安装 APK（上传文件流式安装）。flag: '' 覆盖安装 / -r 替换 / -g 授权。"""
    _require_device(serial)
    name = file.filename or "app.apk"
    if not name.lower().endswith(".apk"):
        raise HTTPException(400, "仅支持 .apk 文件")
    if flag not in ("", "-r", "-g"):
        raise HTTPException(400, "非法安装参数")
    tmp = os.path.join(tempfile.gettempdir(), f"twb_install_{int(time.time()*1000)}_{name}")
    with open(tmp, "wb") as f:
        f.write(file.file.read())
    try:
        args = ["adb", "-s", serial, "install"]
        if flag:
            args.append(flag)
        args.append(tmp)
        r = _run(args, timeout=180)
        output = (r.stdout + r.stderr).strip()
        ok = r.returncode == 0 and "Success" in output
        return {"ok": ok, "output": output}
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


@router.post("/devices/{serial}/uninstall")
def device_uninstall(serial: str, package: str, flag: str = ""):
    _require_device(serial)
    if not _PKG_RE.match(package or ""):
        raise HTTPException(400, "非法包名")
    args = ["adb", "-s", serial, "uninstall"]
    if flag == "-k":
        args.append("-k")
    args.append(package)
    r = _run(args, timeout=60)
    output = (r.stdout + r.stderr).strip()
    return {"ok": r.returncode == 0, "output": output}


@router.post("/devices/{serial}/clear")
def device_clear(serial: str, package: str):
    _require_device(serial)
    if not _PKG_RE.match(package or ""):
        raise HTTPException(400, "非法包名")
    r = _run(["adb", "-s", serial, "shell", "pm", "clear", package], timeout=30)
    output = (r.stdout + r.stderr).strip()
    return {"ok": r.returncode == 0, "output": output}


@router.post("/devices/{serial}/launch")
def device_launch(serial: str, package: str):
    _require_device(serial)
    if not _PKG_RE.match(package or ""):
        raise HTTPException(400, "非法包名")
    r = _run(["adb", "-s", serial, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"], timeout=30)
    output = (r.stdout + r.stderr).strip()
    return {"ok": r.returncode == 0, "output": output}


@router.get("/devices/{serial}/activity")
def device_activity(serial: str):
    """当前焦点 Activity。"""
    _require_device(serial)
    r = _run(["adb", "-s", serial, "shell", "dumpsys", "window", "|", "grep", "mCurrentFocus"], timeout=15)
    m = re.search(r"mCurrentFocus=Window\{[^}]*?\s+([\w.]+/[\w.]+)\}", r.stdout or "")
    return {"activity": m.group(1) if m else ""}


@router.get("/devices/{serial}/screencap")
def device_screencap(serial: str):
    """截图（返回 PNG）。"""
    _require_device(serial)
    with _lock:
        p = subprocess.run(
            ["adb", "-s", serial, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=20,
        )
    if p.returncode != 0 or not p.stdout:
        raise HTTPException(500, "截图失败：" + p.stderr.decode(errors="replace")[:200])
    return Response(content=p.stdout, media_type="image/png")


@router.post("/devices/{serial}/shell")
def device_shell(serial: str, cmd: str = Body(..., embed=True)):
    """执行任意 shell 命令。"""
    _require_device(serial)
    if not cmd or len(cmd) > 500:
        raise HTTPException(400, "命令非法")
    r = _run(["adb", "-s", serial, "shell", cmd], timeout=30)
    return {"code": r.returncode, "output": (r.stdout + r.stderr)[:20000]}


# ---------------- logcat 实时流（WebSocket） ----------------
@ws_router.websocket("/{serial}/logcat")
async def logcat_stream(ws: WebSocket, serial: str, buffer: str = "all"):
    await ws.accept()
    if not _valid_serial(serial):
        await ws.send_json({"error": "非法设备序列号"})
        await ws.close()
        return
    devs = {d["serial"]: d["state"] for d in _list_devices()}
    if devs.get(serial) != "device":
        await ws.send_json({"error": "设备不在线或未授权"})
        await ws.close()
        return
    if buffer not in ("all", "main", "system", "events", "crash"):
        buffer = "all"
    proc = None
    try:
        packages_by_uid, processes_by_pid = await asyncio.gather(
            asyncio.to_thread(_load_package_uid_map, serial),
            asyncio.to_thread(_load_process_map, serial),
        )
        process_refresh_at = time.monotonic()
        args = [
            "adb", "-s", serial, "logcat",
            "-T", "1",  # 跳过设备缓冲区的历史日志，连接即实时；历史可用 dump 接口按需拉取
            "-v", "threadtime", "-v", "uid", "-v", "year",
        ]
        if buffer == "all":
            # Android Studio 默认合并 main+system+crash 三个缓冲区
            args += ["-b", "main", "-b", "system", "-b", "crash"]
        else:
            args += ["-b", buffer]
        # 必须用异步子进程：同步 Popen + readline 会阻塞 uvicorn 事件循环，
        # 导致日志分析开启期间其他接口全部排队超时
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert proc.stdout is not None
        last_dev_check = time.monotonic()
        while True:
            # 周期性校验设备在线：设备掉线时 adb logcat 进程可能挂起不退出，
            # 若不做检查，WebSocket 会一直"活着"而日志静止，前端无从感知
            if time.monotonic() - last_dev_check >= 30:
                devs = {d["serial"]: d["state"] for d in await asyncio.to_thread(_list_devices)}
                if devs.get(serial) != "device":
                    await ws.send_json({"type": "error", "error": "设备已断开，日志流已停止"})
                    break
                last_dev_check = time.monotonic()
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
            except asyncio.TimeoutError:
                continue
            if not line:
                break
            text = line.decode("utf-8", "replace").rstrip("\r\n")
            record = build_log_record(text, packages_by_uid, processes_by_pid)
            if (
                record.get("parsed")
                and record.get("pid") not in processes_by_pid
                and time.monotonic() - process_refresh_at >= 5
            ):
                processes_by_pid = await asyncio.to_thread(_load_process_map, serial)
                process_refresh_at = time.monotonic()
                record = build_log_record(text, packages_by_uid, processes_by_pid)
            await ws.send_json(record)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        if proc:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------- 投屏：H.264 裸流（WebSocket，30fps） ----------------
_SCREEN_BITRATE = "8000000"  # 8Mbps：30fps 下平衡流畅与清晰（原 4Mbps 偏糊）


@ws_router.websocket("/{serial}/stream")
async def screen_stream(ws: WebSocket, serial: str, size: str = ""):
    """adb exec-out screenrecord --output-format=h264 裸流经 WS 转发，客户端用 jmuxer 解码。
    size 可选（如 720x1520）降低传输与解码开销；screenrecord 单次限 180s，结束后自动续流。"""
    await ws.accept()
    if not _valid_serial(serial):
        await ws.send_json({"error": "非法设备序列号"})
        await ws.close()
        return
    devs = {d["serial"]: d["state"] for d in _list_devices()}
    if devs.get(serial) != "device":
        await ws.send_json({"error": "设备不在线或未授权"})
        await ws.close()
        return
    if size and not re.match(r"^\d+x\d+$", size):
        size = ""
    # 先发设备分辨率，供前端坐标映射
    props = _device_props(serial)
    await ws.send_json({"type": "meta", "resolution": props.get("resolution") or ""})
    createflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = None
    try:
        while True:
            args = ["adb", "-s", serial, "exec-out", "screenrecord",
                    "--output-format=h264", "--bit-rate", _SCREEN_BITRATE,
                    "--time-limit", "180"]
            if size:
                args += ["--size", size]
            args += ["-"]
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                creationflags=createflags,
            )
            assert proc.stdout is not None
            try:
                while True:
                    chunk = await proc.stdout.read(65536)
                    if not chunk:
                        break
                    await ws.send_bytes(chunk)
            except WebSocketDisconnect:
                raise
            except Exception:  # noqa: BLE001
                pass
            if ws.client_state.name != "CONNECTED":
                break
            # 180s 自然结束，自动续流
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        if proc and proc.returncode is None:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------- 投屏控制（点击/滑动/长按，WebSocket） ----------------
@ws_router.websocket("/{serial}/control")
async def screen_control(ws: WebSocket, serial: str):
    """接收 JSON：{"type":"tap","x":..,"y":..} / {"type":"swipe","x1":..,"y1":..,"x2":..,"y2":..,"duration":..} / {"type":"longtap","x":..,"y":..}
    使用长驻 adb shell 会话执行 input 命令，避免每次操作启动 adb 进程（显著降低操作延迟）。"""
    await ws.accept()
    if not _valid_serial(serial):
        await ws.close()
        return
    devs = {d["serial"]: d["state"] for d in _list_devices()}
    if devs.get(serial) != "device":
        await ws.close()
        return
    import json
    createflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    shell_proc = None
    try:
        shell_proc = await asyncio.create_subprocess_exec(
            "adb", "-s", serial, "shell",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL, creationflags=createflags,
        )
    except Exception:  # noqa: BLE001
        shell_proc = None

    async def _input(cmd: str):
        """向长驻 shell 写命令；失败则回退为一次性 adb shell。"""
        nonlocal shell_proc
        if shell_proc is None:
            subprocess.run(["adb", "-s", serial, "shell", cmd],
                           capture_output=True, timeout=15, creationflags=createflags)
            return
        try:
            shell_proc.stdin.write((cmd + "\n").encode())
            await shell_proc.stdin.drain()
        except Exception:  # noqa: BLE001
            # 会话失效：销毁并回退一次性执行
            try:
                shell_proc.kill()
            except Exception:  # noqa: BLE001
                pass
            shell_proc = None
            subprocess.run(["adb", "-s", serial, "shell", cmd],
                           capture_output=True, timeout=15, creationflags=createflags)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            t = msg.get("type")
            def _num(v):
                try:
                    return int(round(float(v)))
                except (TypeError, ValueError):
                    return 0
            if t == "tap":
                x, y = _num(msg.get("x")), _num(msg.get("y"))
                await _input(f"input tap {x} {y}")
            elif t == "longtap":
                x, y = _num(msg.get("x")), _num(msg.get("y"))
                await _input(f"input swipe {x} {y} {x} {y} 700")
            elif t == "drag":
                # 真实连续触摸流（对标 scrcpy）：DOWN / MOVE / UP / CANCEL
                action = str(msg.get("action") or "").upper()
                x, y = _num(msg.get("x")), _num(msg.get("y"))
                if action in ("DOWN", "MOVE", "UP", "CANCEL"):
                    await _input(f"input motionevent {action} {x} {y}")
            elif t == "swipe":
                x1, y1 = _num(msg.get("x1")), _num(msg.get("y1"))
                x2, y2 = _num(msg.get("x2")), _num(msg.get("y2"))
                dur = max(50, min(3000, _num(msg.get("duration", 300))))
                await _input(f"input swipe {x1} {y1} {x2} {y2} {dur}")
            elif t == "keyevent":
                keycode = _num(msg.get("keycode"))
                if 0 < keycode < 300:
                    await _input(f"input keyevent {keycode}")
            elif t == "text":
                text = str(msg.get("text") or "")[:2000]
                if text:
                    # Android input text：\ % " $ ` 需转义，空格用 %s（参考 scrcpy 转义规则）
                    escaped = (text.replace("\\", "\\\\").replace("%", "\\%")
                               .replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
                               .replace(" ", "%s"))
                    await _input(f'input text "{escaped}"')
            elif t == "paste":
                text = str(msg.get("text") or "")[:2000]
                if text:
                    if all(ord(c) < 128 for c in text):
                        # 纯 ASCII：input text 直达最可靠
                        escaped = (text.replace("\\", "\\\\").replace("%", "\\%")
                                   .replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
                                   .replace(" ", "%s"))
                        await _input(f'input text "{escaped}"')
                    else:
                        # 含中文等非 ASCII：设置设备剪贴板后模拟粘贴（Android 10+ cmd clipboard）
                        cl = (text.replace("\\", "\\\\").replace('"', '\\"')
                              .replace("$", "\\$").replace("`", "\\`"))
                        await _input(f'cmd clipboard set-text "{cl}"')
                        await asyncio.sleep(0.3)
                        await _input("input keyevent 279")  # KEYCODE_PASTE
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        if shell_proc is not None:
            try:
                if shell_proc.stdin:
                    shell_proc.stdin.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                shell_proc.terminate()
            except Exception:  # noqa: BLE001
                pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------- 通用命令执行（前缀解析，对应本地 ADB 工具 executeCommand） ----------------
_ALLOWED_PREFIX = (
    "shell", "exec-out", "pull", "push", "reboot", "install", "uninstall",
    "get-serialno", "connect", "disconnect", "logcat", "screencap", "screenrecord",
    "devices", "version",
)
_DANGEROUS = ("rm -rf /", "format", "wipe", "dd if=")


@router.post("/devices/{serial}/execute")
def device_execute(serial: str, command: str = Body(..., embed=True)):
    """通用 ADB 命令执行：自动解析命令前缀并串行执行。
    支持 shell/exec-out/pull/push/reboot/install/uninstall/get-serialno/logcat 等前缀。
    屏蔽 rm -rf /、format、wipe 等破坏性命令。"""
    _require_device(serial)
    cmd = (command or "").strip()
    if not cmd or len(cmd) > 1000:
        raise HTTPException(400, "命令非法")
    low = cmd.lower()
    if any(d in low for d in _DANGEROUS):
        raise HTTPException(400, "该命令被安全策略拦截")
    head = cmd.split(None, 1)[0].lower()
    if head not in _ALLOWED_PREFIX:
        raise HTTPException(400, f"不支持的命令前缀：{head}（支持 {', '.join(_ALLOWED_PREFIX)}）")
    if head in ("shell", "exec-out"):
        # shell/exec-out 的剩余部分必须作为单个参数传给 adb，设备端 sh 才能正确解析
        # 分号多命令（如 "shell a;echo;shell b"）与带空格的参数
        rest = cmd.split(None, 1)[1] if " " in cmd else ""
        args = ["adb", "-s", serial, head, rest]
    else:
        args = ["adb", "-s", serial] + cmd.split()
    r = _run(args, timeout=180)
    output = (r.stdout + r.stderr)[:40000]
    return {"code": r.returncode, "output": output}


# ---------------- 电源与模式控制 ----------------
@router.post("/devices/{serial}/reboot")
def device_reboot(serial: str, mode: str = "normal"):
    """重启：normal / bootloader / recovery。"""
    _require_device(serial)
    if mode not in ("normal", "bootloader", "recovery"):
        raise HTTPException(400, "非法重启模式")
    cmd = ["adb", "-s", serial, "reboot"] + ([] if mode == "normal" else [mode])
    r = _run(cmd, timeout=30)
    return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()}


@router.post("/devices/{serial}/shutdown")
def device_shutdown(serial: str):
    """关机：三策略依次尝试。"""
    _require_device(serial)
    createflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    attempts = [
        ["adb", "-s", serial, "reboot", "-p"],
        ["adb", "-s", serial, "shell", "cmd", "power", "shutdown"],
        ["adb", "-s", serial, "shell", "am", "broadcast", "-a", "android.intent.action.ACTION_REQUEST_SHUTDOWN",
         "--ez", "KEY_CONFIRM", "true", "--user", "0"],
    ]
    results = []
    for args in attempts:
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=30,
                               encoding="utf-8", errors="replace", creationflags=createflags)
            out = (r.stdout + r.stderr).strip()
            results.append(out)
            if not out or not re.search(r"error|failed|denied|unknown|exception", out, re.I):
                return {"ok": True, "output": f"已发送关机指令：{' '.join(args[3:])}"}
        except Exception as e:  # noqa: BLE001
            results.append(str(e))
    return {"ok": False, "output": "；".join(results)[:500]}


# ---------------- 统一保存目录设置 ----------------
_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "adb_settings.json")
# adbtools.py -> api/v1 -> app -> backend -> Test-Bench/adb_settings.json
_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adb_settings.json")


def _get_save_dir():
    """返回保存目录配置：相对路径（相对 uploads）或本机绝对路径。"""
    try:
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f).get("save_dir", "") or ""
            if d:
                d = d.strip()
                # 相对路径：字母数字_/-
                if re.match(r"^[A-Za-z0-9_/\-]+$", d) and ".." not in d:
                    return d.strip("/")
                # 绝对路径：必须是已存在的目录
                if os.path.isabs(d) and os.path.isdir(d):
                    return d
    except (OSError, ValueError):
        pass
    return ""


def _resolve_save_dir():
    """把保存目录配置解析为最终绝对目录（自动创建相对目录）。"""
    d = _get_save_dir()
    if os.path.isabs(d):
        return d
    if d:
        from app.api.v1.upload import UPLOAD_DIR
        p = os.path.join(str(UPLOAD_DIR), d)
        os.makedirs(p, exist_ok=True)
        return p
    return None


@router.get("/settings")
def get_settings():
    return {"save_dir": _get_save_dir()}


@router.post("/settings")
def set_settings(save_dir: str = Body("", embed=True)):
    d = (save_dir or "").strip().strip("/")
    if d:
        if ".." in d:
            raise HTTPException(400, "保存目录不能包含 ..")
        if os.path.isabs(d):
            # 本机绝对路径：必须已存在且为目录
            if not os.path.isdir(d):
                raise HTTPException(400, f"目录不存在或不可访问：{d}")
        elif not re.match(r"^[A-Za-z0-9_/\-]+$", d):
            raise HTTPException(400, "相对保存目录只能包含字母数字_/-(如 records)")
    try:
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"save_dir": d}, f, ensure_ascii=False)
    except OSError as e:
        raise HTTPException(500, f"保存设置失败：{e}") from e
    return {"ok": True, "save_dir": d}


# ---------------- 本机目录浏览（保存目录选择器用，只读） ----------------
@router.get("/browse")
def browse_dir(path: str = ""):
    """浏览本机目录：path 为空返回盘符列表；否则列出该目录下的子目录。"""
    if not path:
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            root = f"{letter}:\\"
            if os.path.exists(root):
                try:
                    drives.append({"name": root, "path": root, "is_dir": True})
                except OSError:
                    pass
        return {"path": "", "parent": "", "items": drives}
    try:
        real = os.path.realpath(path)
    except OSError:
        real = path
    if not os.path.isdir(real):
        raise HTTPException(400, f"目录不存在或不可访问：{path}")
    items = []
    try:
        names = sorted(os.listdir(real))
    except OSError as e:
        raise HTTPException(400, f"无法读取目录：{e}") from e
    for n in names:
        full = os.path.join(real, n)
        try:
            if os.path.isdir(full):
                items.append({"name": n, "path": full, "is_dir": True})
        except OSError:
            continue
    parent = os.path.dirname(real) if real and os.path.dirname(real) != real else ""
    return {"path": real, "parent": parent, "items": items}


# ---------------- 录屏（录制并拉取到平台，自动清理设备文件） ----------------
@router.post("/devices/{serial}/record")
def device_record(serial: str, duration: int = 10, resolution: str = "", filename: str = ""):
    """录屏：设备端 screenrecord → 拉取到 uploads（可配置子目录）→ 删除设备文件。返回附件 URL。"""
    _require_device(serial)
    if duration < 1 or duration > 180:
        raise HTTPException(400, "时长需在 1-180 秒")
    from app.api.v1.upload import UPLOAD_DIR
    import uuid
    name = (filename or f"record_{int(time.time())}.mp4").strip()
    if not name.lower().endswith(".mp4"):
        name += ".mp4"
    device_path = f"/sdcard/{name}"
    args = ["adb", "-s", serial, "shell", "screenrecord"]
    if resolution and re.match(r"^\d+x\d+$", resolution):
        args += ["--size", resolution]
    args += ["--time-limit", str(duration), device_path]
    r = _run(args, timeout=duration + 30)
    if r.returncode != 0 and "error" in (r.stderr or "").lower():
        raise HTTPException(500, "录屏失败：" + (r.stderr or "")[:200])
    sub = _get_save_dir()
    save_dir = _resolve_save_dir() or str(UPLOAD_DIR)
    fname = f"{uuid.uuid4().hex[:20]}_{name}"
    dest = os.path.join(save_dir, fname)
    p = _run(["adb", "-s", serial, "pull", device_path, dest], timeout=120)
    _run(["adb", "-s", serial, "shell", "rm", device_path], timeout=20)
    if p.returncode != 0 or not os.path.exists(dest):
        raise HTTPException(500, "录屏拉取失败")
    if os.path.isabs(sub):
        url = ""
    else:
        url = f"/uploads/{sub + '/' if sub else ''}{fname}"
    return {"ok": True, "url": url, "name": name, "local_path": dest}


# ---------------- 录屏（手动开始/停止，分段录制绕过 180s 上限） ----------------
_record_sessions: dict[str, dict] = {}


def _find_ffmpeg():
    try:
        import shutil
        p = shutil.which("ffmpeg")
        if p:
            return p
    except Exception:  # noqa: BLE001
        pass
    for cand in (
        r"D:\Test App Install Position\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.0.2-full_build\bin\ffmpeg.exe"),
    ):
        if os.path.exists(cand):
            return cand
    return "ffmpeg"


def _record_loop(sess: dict):
    """分段录屏循环：每段 170s，stop 事件可立即终止当前段。不持有全局 adb 锁。"""
    serial = sess["serial"]
    createflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    while not sess["stop"].is_set():
        with sess["lock"]:
            idx = sess["next_idx"]
            sess["next_idx"] += 1
        dev = f"/sdcard/{sess['base']}_{idx:03d}.mp4"
        args = ["adb", "-s", serial, "shell", "screenrecord"]
        if sess["resolution"] and re.match(r"^\d+x\d+$", sess["resolution"]):
            args += ["--size", sess["resolution"]]
        args += ["--time-limit", "170", dev]
        try:
            # Popen 非阻塞启动，轮询等待，stop 时立即 kill 当前段
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=createflags)
            while proc.poll() is None:
                if sess["stop"].is_set():
                    proc.kill()
                    break
                time.sleep(0.3)
            try:
                proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            break
        if sess["stop"].is_set():
            break


@router.post("/devices/{serial}/record/start")
def record_start(serial: str, resolution: str = "", filename: str = ""):
    """开始分段录屏（手动结束）。"""
    _require_device(serial)
    old = _record_sessions.get(serial)
    if old and old.get("running"):
        raise HTTPException(400, "已有录制正在进行，请先结束")
    base = (filename or f"record_{int(time.time())}").strip()
    if base.lower().endswith(".mp4"):
        base = base[:-4]
    sess = {
        "serial": serial, "base": base, "next_idx": 0,
        "stop": threading.Event(), "running": True,
        "resolution": resolution or "", "lock": threading.Lock(),
    }
    _record_sessions[serial] = sess
    t = threading.Thread(target=_record_loop, args=(sess,), daemon=True)
    sess["thread"] = t
    t.start()
    return {"ok": True}


@router.post("/devices/{serial}/record/stop")
def record_stop(serial: str):
    """结束录屏：停止分段 → 拉取全部片段 → ffmpeg 合并 → 返回视频。"""
    sess = _record_sessions.get(serial)
    if not sess:
        raise HTTPException(400, "当前没有进行中的录制")
    with sess["lock"]:
        if not sess.get("running"):
            raise HTTPException(400, "当前没有进行中的录制")
        sess["running"] = False
    sess["stop"].set()
    if sess.get("thread"):
        sess["thread"].join(timeout=210)
    _record_sessions.pop(serial, None)
    from app.api.v1.upload import UPLOAD_DIR
    import uuid
    sub = _get_save_dir()
    save_dir = _resolve_save_dir() or str(UPLOAD_DIR)
    os.makedirs(save_dir, exist_ok=True)
    outname = f"{sess['base']}.mp4"
    outpath = os.path.join(save_dir, outname)
    if os.path.exists(outpath):
        os.remove(outpath)
    local_segs = []
    n = sess["next_idx"]
    for i in range(n):
        dev = f"/sdcard/{sess['base']}_{i:03d}.mp4"
        dest = os.path.join(save_dir, f"{uuid.uuid4().hex[:8]}_seg_{i:03d}.mp4")
        r = _run(["adb", "-s", serial, "pull", dev, dest], timeout=120)
        _run(["adb", "-s", serial, "shell", "rm", dev], timeout=20)
        if r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
            local_segs.append(dest)
        elif os.path.exists(dest):
            try:
                os.remove(dest)
            except OSError:
                pass
    if not local_segs:
        raise HTTPException(500, "录屏失败：未获取到有效片段")
    if len(local_segs) == 1:
        os.replace(local_segs[0], outpath)
    else:
        import tempfile
        fd, lst = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for s in local_segs:
                f.write(f"file '{s.replace(chr(39), chr(39) * 2)}'\n")
        try:
            subprocess.run(
                [_find_ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", outpath],
                capture_output=True, text=True, timeout=300,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        finally:
            try:
                os.remove(lst)
            except OSError:
                pass
        for s in local_segs:
            try:
                if os.path.exists(s):
                    os.remove(s)
            except OSError:
                pass
        if not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
            raise HTTPException(500, "录屏合并失败")
    if os.path.isabs(sub):
        url = ""
    else:
        url = f"/uploads/{sub + '/' if sub else ''}{outname}"
    return {"ok": True, "url": url, "name": outname, "local_path": outpath}


# ---------------- Logcat 导出 / 清空 / 进程列表 ----------------
@router.get("/devices/{serial}/processes")
def device_processes(serial: str):
    """设备运行进程列表（PID + 进程名），供日志分析按进程/包名过滤。

    toybox `ps -A` 默认列序：USER PID PPID VSZ RSS WCHAN ADDR S NAME
    进程名即应用包名（或 包名:子进程），系统内核线程以 [ 开头。
    """
    _require_device(serial)
    try:
        process_map = _load_process_map(serial)
    except subprocess.TimeoutExpired:
        return {"ok": False, "processes": []}
    procs = [{"pid": int(pid), "name": name} for pid, name in process_map.items()]
    procs.sort(key=lambda p: p["pid"])
    return {"ok": True, "processes": procs}


@router.get("/devices/{serial}/logcat/dump")
def device_logcat_dump(serial: str, lines: int = 500):
    """导出最近日志（logcat -d）。"""
    _require_device(serial)
    if lines < 1 or lines > 5000:
        raise HTTPException(400, "行数需在 1-5000")
    r = _run(["adb", "-s", serial, "logcat", "-d", "-v", "threadtime", "-t", str(lines)], timeout=30)
    return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr)[:100000]}


@router.post("/devices/{serial}/logcat/clear")
def device_logcat_clear(serial: str):
    """清空设备 logcat 缓冲区。"""
    _require_device(serial)
    r = _run(["adb", "-s", serial, "logcat", "-c"], timeout=15)
    return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()}
_MONKEY_REPORT_RE = re.compile(r"^monkey_\d{8}_\d{6}_[0-9a-f]{12}\.txt$")
_MONKEY_PROCESS = "com.android.commands.monkey"
_monkey_runs_lock = threading.Lock()
_monkey_runs: set[str] = set()


def _monkey_pids(serial: str) -> list[int]:
    """只识别设备上的 Android Monkey 进程，不匹配应用包名。"""
    for command in (["ps", "-A", "-o", "PID,NAME"], ["ps", "-A"]):
        result = _run(["adb", "-s", serial, "shell", *command], timeout=10)
        if result.returncode == 0:
            pids = []
            for line in result.stdout.splitlines()[1:]:
                fields = line.split()
                if fields and fields[-1] == _MONKEY_PROCESS:
                    pid = fields[0] if command[-1] == "PID,NAME" else fields[1]
                    if pid.isdecimal():
                        pids.append(int(pid))
            return pids
    raise HTTPException(502, "无法读取设备进程状态，请检查 ADB 连接")


def _stop_monkey_pids(serial: str) -> list[int]:
    pids = _monkey_pids(serial)
    for pid in pids:
        result = _run(["adb", "-s", serial, "shell", "kill", str(pid)], timeout=10)
        if result.returncode != 0 and pid in _monkey_pids(serial):
            raise HTTPException(502, f"停止 Monkey 进程 {pid} 失败")
    for _ in range(5):
        remaining = _monkey_pids(serial)
        if not remaining:
            return pids
        time.sleep(0.2)
    for pid in _monkey_pids(serial):
        _run(["adb", "-s", serial, "shell", "kill", "-9", str(pid)], timeout=10)
    for _ in range(5):
        if not _monkey_pids(serial):
            return pids
        time.sleep(0.2)
    raise HTTPException(502, "已发送停止指令，但设备上的 Monkey 仍在运行")


def _monkey_report_dir(serial: str) -> Path:
    if not _valid_serial(serial):
        raise HTTPException(400, "非法设备序列号")
    from app.api.v1.upload import UPLOAD_DIR
    device_key = hashlib.sha256(serial.encode("utf-8")).hexdigest()[:16]
    return UPLOAD_DIR / "monkey_reports" / device_key


def _monkey_report_file(serial: str, name: str) -> Path:
    if not _MONKEY_REPORT_RE.fullmatch(name):
        raise HTTPException(404, "报告不存在")
    directory = _monkey_report_dir(serial)
    target = directory / name
    if target.is_symlink() or not target.is_file() or target.resolve().parent != directory.resolve():
        raise HTTPException(404, "报告不存在")
    return target


def _monkey_report_info(serial: str, path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "url": f"/api/v1/adb/devices/{serial}/monkey/reports/{path.name}/file",
    }


@router.get("/devices/{serial}/monkey/reports")
def list_monkey_reports(serial: str):
    directory = _monkey_report_dir(serial)
    directory.mkdir(parents=True, exist_ok=True)
    reports = [
        _monkey_report_info(serial, path)
        for path in directory.iterdir()
        if _MONKEY_REPORT_RE.fullmatch(path.name) and path.is_file() and not path.is_symlink()
    ]
    reports.sort(key=lambda report: report["created_at"], reverse=True)
    return {"reports": reports, "directory": str(directory)}


@router.get("/devices/{serial}/monkey/status")
def device_monkey_status(serial: str):
    _require_device(serial)
    pids = _monkey_pids(serial)
    return {"running": bool(pids), "pids": pids}


@router.post("/devices/{serial}/monkey/stop")
def device_monkey_stop(serial: str):
    _require_device(serial)
    pids = _stop_monkey_pids(serial)
    return {"ok": True, "stopped": bool(pids), "pids": pids}


@router.get("/devices/{serial}/monkey/reports/{name}/file")
def view_monkey_report(serial: str, name: str):
    path = _monkey_report_file(serial, name)
    return FileResponse(path, media_type="text/plain; charset=utf-8", filename=name, content_disposition_type="inline")


@router.delete("/devices/{serial}/monkey/reports/{name}")
def delete_monkey_report(serial: str, name: str):
    path = _monkey_report_file(serial, name)
    path.unlink()
    return {"ok": True}


@router.post("/devices/{serial}/monkey")
def device_monkey(
    serial: str,
    package: str = "",
    events: int = 200,
    throttle: int = 100,
    pct_touch: int = 35,
    pct_motion: int = 20,
    pct_nav: int = 10,
    pct_majornav: int = 15,
    pct_pinchzoom: int | None = None,
    pct_rotation: int | None = None,
    pct_syskeys: int | None = None,
    pct_appswitch: int | None = None,
    pct_permission: int | None = None,
    pct_anyevent: int | None = None,
    ignore: bool = True,
):
    """Monkey 随机压力测试。events 建议 50-1000，支持事件占比与忽略崩溃配置。"""
    _require_device(serial)
    if events < 1 or events > 10000:
        raise HTTPException(400, "事件数需在 1-10000")
    ratios = (
        ("touch", pct_touch), ("motion", pct_motion), ("pinchzoom", pct_pinchzoom),
        ("rotation", pct_rotation), ("nav", pct_nav),
        ("majornav", pct_majornav), ("syskeys", pct_syskeys),
        ("appswitch", pct_appswitch),
        ("permission", pct_permission), ("anyevent", pct_anyevent),
    )
    specified = [value for _, value in ratios if value is not None]
    if any(value < 0 or value > 100 for value in specified):
        raise HTTPException(400, "事件占比需为 0-100 的整数")
    if sum(specified) > 100 or (len(specified) == len(ratios) and sum(specified) != 100):
        raise HTTPException(400, "事件占比总和不能超过 100%；全部填写时总和必须为 100%")
    args = [
        "adb", "-s", serial, "shell", "monkey", "-v", "--throttle", str(max(0, throttle)),
        "--pct-trackball", "0", "--pct-flip", "0",
    ]
    if package:
        if not _PKG_RE.match(package):
            raise HTTPException(400, "非法包名")
        args += ["-p", package]
    for name, value in ratios:
        if value is not None:
            args += [f"--pct-{name}", str(value)]
    if ignore:
        args += ["--ignore-crashes", "--ignore-timeouts", "--ignore-security-exceptions"]
    args += [str(events)]
    with _monkey_runs_lock:
        if serial in _monkey_runs:
            raise HTTPException(409, "该设备已有 Monkey 测试正在执行")
        _monkey_runs.add(serial)
    try:
        return _execute_monkey(serial, package, events, throttle, ratios, args)
    finally:
        with _monkey_runs_lock:
            _monkey_runs.discard(serial)


def _execute_monkey(serial, package, events, throttle, ratios, args):
    if _monkey_pids(serial):
        raise HTTPException(409, "设备上已有 Monkey 进程，请先检测并停止")
    directory = _monkey_report_dir(serial)
    name = f"monkey_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:12]}.txt"
    path = directory / name
    timeout = min(14400, max(180, int(events * (max(0, throttle) / 1000 + 0.5) + 60)))
    ok = False
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with path.open("xb", buffering=0) as report:
            header = (
                f"Monkey 测试日志\n开始时间：{datetime.now().astimezone().isoformat()}\n"
                f"设备：{serial}\n目标包：{package or '全系统'}\n"
                f"事件数：{events}\n节流：{max(0, throttle)} ms\n"
                f"事件占比：{', '.join(f'{key}={value}%' for key, value in ratios if value is not None)}\n"
                "\n--- Monkey 输出 ---\n"
            )
            report.write(header.encode("utf-8"))
            report.flush()
            try:
                result = subprocess.run(args, stdout=report, stderr=subprocess.STDOUT, timeout=timeout)
                status = f"退出码 {result.returncode}"
                try:
                    remaining = _monkey_pids(serial)
                    ok = result.returncode == 0 and not remaining
                    if remaining:
                        status += "；设备上的 Monkey 仍在运行"
                except HTTPException:
                    status += "；无法确认设备进程已停止"
            except subprocess.TimeoutExpired:
                status = f"运行超时（{timeout} 秒）"
                try:
                    _stop_monkey_pids(serial)
                    status += "；已停止设备上的 Monkey"
                except HTTPException as exc:
                    status += f"；{exc.detail}"
            except OSError as exc:
                status = f"执行失败：{exc}"
            report.write(f"\n--- 结束 ---\n结束时间：{datetime.now().astimezone().isoformat()}\n状态：{status}\n".encode("utf-8"))
    except OSError as exc:
        raise HTTPException(500, "无法保存 Monkey 测试报告") from exc
    with path.open("rb") as report:
        report.seek(0, os.SEEK_END)
        report.seek(max(0, report.tell() - 8192))
        output = report.read().decode("utf-8", errors="replace")[-4000:]
    return {"ok": ok, "output": output, "report": _monkey_report_info(serial, path)}


# ---------------- 通知触发（黑盒快速触发定时通知） ----------------
# dumpsys jobscheduler 输出形如：
#   JOB #u0a293/1: b77177a com.ksg.test/androidx.work.impl.background.systemjob.SystemJobService
#   JOB #u0a293/2001: 7cfdcde com.ksg.test/com.calc.finance.ttgs.platform.reminder.scheduling.job.UsageReminderJobService
_JOB_RE = re.compile(r"JOB #u0a\d+/(\d+): [0-9a-f]+ (\S+?)/(\S+)")

@router.get("/devices/{serial}/notify/jobs")
def device_notify_jobs(serial: str, pkg: str = "com.kjshd.calu.test"):
    """解析指定包名的 JobScheduler/WorkManager 定时任务 ID。"""
    pkg = (pkg or "").strip() or "com.kjshd.calu.test"
    _require_device(serial)
    r = _run(["adb", "-s", serial, "shell", "dumpsys", "jobscheduler"], timeout=25)
    if r.returncode != 0:
        raise HTTPException(400, (r.stderr or "dumpsys jobscheduler 执行失败").strip()[-300:])
    jobs = []
    for ln in (r.stdout or "").splitlines():
        if pkg not in ln:
            continue
        m = _JOB_RE.search(ln)
        if not m:
            continue
        job_id, svc = int(m.group(1)), m.group(3)
        # 按通知类型分类：WorkManager 15 分钟循环 / UsageReminder 30 分钟
        jtype = 2 if "SystemJobService" in svc else (1 if "UsageReminderJobService" in svc else 0)
        jobs.append({"id": job_id, "service": svc, "type": jtype})
    # 去重（同一 job 可能在多行出现）
    seen, uniq = set(), []
    for j in jobs:
        k = (j["type"], j["id"])
        if k not in seen:
            seen.add(k)
            uniq.append(j)
    return {"ok": True, "jobs": uniq}


@router.post("/devices/{serial}/notify/trigger")
def device_notify_trigger(serial: str, type: int = 1, job_id: int = 0, pkg: str = "com.kjshd.calu.test"):
    """黑盒快速触发定时通知。
    type=1：30 分钟通知（JobScheduler 直接强弹）；
    type=2：15 分钟循环通知（WorkManager 有内部时钟保护，先时区欺骗再强弹，最后恢复时区）。
    """
    pkg = (pkg or "").strip() or "com.kjshd.calu.test"
    _require_device(serial)
    if job_id < 0:
        raise HTTPException(400, "任务 ID 非法（JobScheduler 任务 ID 允许为 0）")
    steps = []
    if type == 1:
        r = _run(["adb", "-s", serial, "shell", "cmd", "jobscheduler", "run", "-f", pkg, str(job_id)], timeout=30)
        steps.append({"cmd": f"强弹 30 分钟通知（{pkg} job {job_id}）", "ok": r.returncode == 0, "out": (r.stdout + r.stderr).strip()[-800:]})
    elif type == 2:
        r1 = _run(["adb", "-s", serial, "shell", "settings", "put", "global", "auto_timezone", "0"], timeout=20)
        steps.append({"cmd": "关闭自动时区", "ok": r1.returncode == 0, "out": (r1.stdout + r1.stderr).strip()[-400:]})
        r2 = _run(["adb", "-s", serial, "shell", "service", "call", "alarm", "3", "s16", "Asia/Anadyr"], timeout=20)
        steps.append({"cmd": "时区调快（Asia/Anadyr，时间暴涨 4 小时）", "ok": r2.returncode == 0, "out": (r2.stdout + r2.stderr).strip()[-400:]})
        r3 = _run(["adb", "-s", serial, "shell", "cmd", "jobscheduler", "run", "-f", pkg, str(job_id)], timeout=30)
        steps.append({"cmd": f"强弹 15 分钟循环通知（{pkg} job {job_id}）", "ok": r3.returncode == 0, "out": (r3.stdout + r3.stderr).strip()[-800:]})
        # 恢复：先手动切回北京时间（auto_timezone=1 依赖网络 NITZ 同步，实测恢复慢/不生效），再开启自动时区
        r4 = _run(["adb", "-s", serial, "shell", "settings", "put", "global", "auto_timezone", "0"], timeout=20)
        r5 = _run(["adb", "-s", serial, "shell", "service", "call", "alarm", "3", "s16", "Asia/Shanghai"], timeout=20)
        r6 = _run(["adb", "-s", serial, "shell", "settings", "put", "global", "auto_timezone", "1"], timeout=20)
        steps.append({"cmd": "恢复北京时间（Asia/Shanghai）", "ok": r4.returncode == 0 and r5.returncode == 0 and r6.returncode == 0, "out": (r6.stdout + r6.stderr).strip()[-400:]})
    else:
        raise HTTPException(400, "type 仅支持 1（30 分钟）或 2（15 分钟循环）")
    return {"ok": all(s["ok"] for s in steps), "steps": steps}


# ---------------- AI 日志分析（复用 AI 模型配置） ----------------
def _call_llm(model, system_prompt: str, user_text: str) -> str:
    import requests
    base = (model.base_url or "").strip().rstrip("/")
    url = base + "/chat/completions" if base else "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {"Authorization": f"Bearer {model.api_key}", "Content-Type": "application/json"}
    body = {
        "model": model.model_name,
        "temperature": model.temperature,
        "max_tokens": model.max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }
    resp = requests.post(url, json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


@router.get("/log-analyze/models")
def log_analyze_models(db=Depends(get_db)):
    """启用的 AI 模型列表（供日志分析选择）。"""
    from app.models.ai import ModelConfig
    ms = db.query(ModelConfig).filter(ModelConfig.status == "enabled").order_by(ModelConfig.id).all()
    return [
        {"id": m.id, "name": m.name, "provider": m.provider, "model_name": m.model_name}
        for m in ms
    ]


@router.post("/devices/{serial}/log-analyze")
def device_log_analyze(
    serial: str,
    lines: list[str] = Body(..., embed=True),
    model_id: int = Body(0, embed=True),
):
    """对 logcat 行做 AI 分析：异常、错误、崩溃、关键事件。"""
    _require_device(serial)
    if not lines:
        raise HTTPException(400, "没有可分析的日志")
    from app.core.database import SessionLocal
    from app.models.ai import ModelConfig
    db = SessionLocal()
    try:
        q = db.query(ModelConfig).filter(ModelConfig.status == "enabled")
        if model_id:
            q = q.filter(ModelConfig.id == model_id)
        model = q.order_by(ModelConfig.id).first()
        if not model:
            raise HTTPException(400, "没有启用的 AI 模型，请先在「AI 模型配置」添加并启用")
        text = "\n".join(lines[-400:])
        system = (
            "你是资深 Android 测试工程师，擅长分析 logcat 日志。"
            "请找出异常、错误、崩溃、ANR、卡顿、内存问题等关键信息，"
            "按严重程度分组，说明原因与建议。用简洁的中文输出，可带编号。"
        )
        result = _call_llm(model, system, f"设备 {serial} 的 logcat 日志片段：\n{text}")
        return {"ok": True, "result": result, "model": model.name}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:300]
        return {"ok": False, "error": f"模型调用失败：{msg}", "model": model.name if 'model' in locals() else ''}
    finally:
        db.close()


# ---------------- 设备文件浏览 / 拉取 ----------------
@router.get("/devices/{serial}/fs")
def device_fs(serial: str, path: str = "/sdcard"):
    """设备文件系统列表。"""
    _require_device(serial)
    if not path or len(path) > 500 or ".." in path:
        raise HTTPException(400, "非法路径")
    # 符号链接目录（如 /sdcard -> /storage/self/primary）展开重试
    for attempt in range(2):
        r = _run(["adb", "-s", serial, "shell", "ls", "-la", path], timeout=15)
        lines = (r.stdout or "").splitlines()
        is_link_dir = any(" -> " in ln for ln in lines)
        if is_link_dir and attempt == 0 and not path.endswith("/"):
            path = path + "/"
            continue
        break
    items = []
    for ln in lines:
        ln = ln.rstrip()
        if not ln:
            continue
        if ln.startswith("total"):
            continue
        parts = ln.split(None, 8)
        # 兼容两种 ls 输出：无日期(9列,文件名 parts[8]) / 有日期(8列,文件名 parts[7])
        if len(parts) < 8:
            continue
        mode = parts[0]
        owner = parts[2]
        group = parts[3]
        size_raw = parts[4]
        name = parts[7] if len(parts) == 8 else parts[8]
        if name in (".", ".."):
            continue
        if mode.startswith("d"):
            typ = "dir"
        elif mode.startswith("l"):
            typ = "link"
        else:
            typ = "file"
        items.append({
            "name": name,
            "type": typ,
            "size": int(size_raw) if size_raw.isdigit() else 0,
            "mode": mode,
            "owner": owner,
            "group": group,
        })
    items.sort(key=lambda i: (i["type"] != "dir", i["name"].lower()))
    return {"path": path, "items": items}


@router.post("/devices/{serial}/fs/pull")
def device_fs_pull(serial: str, path: str = Body(..., embed=True)):
    """拉取设备文件到平台 uploads（可配置子目录），返回附件 URL。"""
    _require_device(serial)
    if not path or len(path) > 500 or ".." in path:
        raise HTTPException(400, "非法路径")
    from app.api.v1.upload import UPLOAD_DIR
    import uuid
    name = os.path.basename(path) or "device_file"
    fname = f"{uuid.uuid4().hex[:20]}_{os.path.basename(name)}"
    sub = _get_save_dir()
    save_dir = _resolve_save_dir() or str(UPLOAD_DIR)
    dest = os.path.join(save_dir, fname)
    r = _run(["adb", "-s", serial, "pull", path, dest], timeout=120)
    if r.returncode != 0 or not os.path.exists(dest):
        raise HTTPException(500, "拉取失败：" + (r.stderr or "")[:200])
    if os.path.isabs(sub):
        url = ""
    else:
        url = f"/uploads/{sub + '/' if sub else ''}{fname}"
    return {"ok": True, "url": url, "name": os.path.basename(name), "local_path": dest}


@router.post("/devices/{serial}/fs/push")
def device_fs_push(serial: str, path: str = Form(...), file: UploadFile = File(...)):
    """推送本地文件到设备当前目录。"""
    _require_device(serial)
    if not path.startswith("/") or len(path) > 500 or ".." in path.split("/") or any(ord(c) < 32 for c in path):
        raise HTTPException(400, "非法路径")
    name = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not name or name in (".", "..") or len(name) > 255 or any(ord(c) < 32 for c in name):
        raise HTTPException(400, "非法文件名")
    dest = f"{path.rstrip('/')}/{name}"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(prefix="twb_push_", delete=False) as tmp_file:
            tmp = tmp_file.name
            shutil.copyfileobj(file.file, tmp_file)
        r = _run(["adb", "-s", serial, "push", tmp, dest], timeout=120)
        output = (r.stdout + r.stderr).strip()
        return {"ok": r.returncode == 0, "output": output}
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass
