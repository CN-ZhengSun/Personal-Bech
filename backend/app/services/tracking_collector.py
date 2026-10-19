"""埋点采集层：ADB 日志采集器 + 实时匹配计数去重 + WebSocket 推送。

- 采集线程读取 `adb logcat -s TAG` 输出流，解析 reportEvents 批量事件
- 事件与清单匹配（eid 精确），按「事件ID + 秒级时间戳」去重（窗口可配置）
- 未录入事件忽略；命中事件更新计数并广播到所有 WebSocket 客户端
"""

import asyncio
import re
import subprocess
import threading
import time
from datetime import datetime

from app.core.database import SessionLocal
from app.models.tracking import TrackingEvent
from app.services.tracking_parser import ReportBuffer


class WSManager:
    """WebSocket 连接管理（进程内单例）。"""

    def __init__(self):
        self._connections: list = []
        self._loop = None
        self._lock = threading.Lock()

    async def connect(self, ws):
        await ws.accept()
        with self._lock:
            if self._loop is None:
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._loop = None
            self._connections.append(ws)

    def disconnect(self, ws):
        with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)

    async def _broadcast(self, payload: dict):
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception as e:
                print("[DBG broadcast] send err", repr(e), flush=True)

    def broadcast(self, payload: dict):
        """线程安全广播（供采集线程调用）。"""
        with self._lock:
            loop = self._loop
            conns = list(self._connections)
        if not loop or not conns:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast(payload), loop)
        except Exception as e:
            print("[DBG broadcast] err", repr(e), flush=True)


ws_manager = WSManager()


class CollectorManager:
    """全局单例：管理采集线程与 adb 子进程。"""

    _lock = threading.Lock()
    _thread: threading.Thread | None = None
    _proc: subprocess.Popen | None = None
    _stop = threading.Event()
    _project_id: int | None = None
    _serial: str | None = None

    def current_project(self):
        return self._project_id

    def current_serial(self):
        return self._serial

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, project_id: int, config: dict, serial: str | None = None) -> bool:
        with self._lock:
            self._stop_locked()
            self._stop = threading.Event()
            self._project_id = project_id
            self._serial = serial
            self._thread = threading.Thread(
                target=self._run, args=(project_id, config, serial), daemon=True
            )
            self._thread.start()
            return True

    def stop(self):
        with self._lock:
            self._stop_locked()

    def _stop_locked(self):
        self._stop.set()
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        self._thread = None
        self._project_id = None
        self._serial = None

    def _run(self, project_id: int, config: dict, serial: str | None = None):
        db = SessionLocal()
        try:
            events = {
                e.event_id: e.id
                for e in db.query(TrackingEvent).filter(TrackingEvent.project_id == project_id).all()
            }
        finally:
            db.close()

        window = int(config.get("dedup_window") or 3)
        # log_tag 数据库里可能带尾冒号（如 "EM:"），统一去尾冒号后再匹配；
        # logcat 输出 tag 后可能有空格填充（如 "I EM      :"），用正则容忍空白
        tag = (config.get("log_tag") or "hk3").rstrip(":")
        tag_re = re.compile(rf"{re.escape(tag)}\s*:")
        dedup: dict[str, int] = {}  # event_id -> 最近秒级时间戳
        buf = ReportBuffer()

        # Samsung/Android16 上 logcat 的 -s tag 过滤可能失效，改用全量输出 + 本地按 tag 过滤；
        # 必须 -s 指定设备，多设备连接时 adb logcat 会报 more than one device
        serial = serial or ""
        cmd = ["adb", "-s", serial, "logcat"] if serial else ["adb", "logcat"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            proc = None
        self._proc = proc
        if proc is None:
            return
        in_batch = False  # 是否处于 reportEvents 多行累积中（此时续行可能无 tag 前缀）
        try:
            while not self._stop.is_set():
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue
                # 本地按 TAG 过滤：目标 tag 行进入；已在解析中的多行 JSON 续行放行
                if tag_re.search(line):
                    in_batch = True
                elif not in_batch and not buf.in_progress:
                    continue
                for ev in buf.feed(line):
                    self._handle_event(project_id, ev, events, dedup, window)
                if not buf.in_progress:
                    in_batch = False
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            self._proc = None

    def _handle_event(self, project_id: int, ev: dict, events: dict, dedup: dict, window: int):
        eid = ev.get("eid")
        if not eid or eid not in events:
            return  # 未录入清单 → 忽略
        ts_sec = int(ev.get("ts") or 0) // 1000 if ev.get("ts") else int(time.time())
        last = dedup.get(eid)
        if last is not None and ts_sec - last < window:
            return  # 去重窗口内
        dedup[eid] = ts_sec

        db = SessionLocal()
        try:
            rec = db.get(TrackingEvent, events[eid])
            if rec is None:
                return
            if rec.is_ignored:
                return  # 清单中已忽略的事件不参与计数与推送
            rec.trigger_count += 1
            rec.last_triggered_at = datetime.now()
            db.commit()
            payload = {
                "event_id": rec.event_id,
                "event_name": rec.event_name,
                "trigger_count": rec.trigger_count,
                "last_triggered_at": rec.last_triggered_at.isoformat()[:19],
                "project_id": project_id,
            }
        finally:
            db.close()
        ws_manager.broadcast(payload)


collector_manager = CollectorManager()
