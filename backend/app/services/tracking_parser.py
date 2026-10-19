"""埋点日志解析器：从 ADB 日志流中提取 reportEvents 批量事件列表。

样例日志（logcat 输出，可能多行格式化 JSON）：
    hk3: reportEvents: [
        { "ts": 1788853625764, "eid": "ad_load_failed_x", "props": {...} }, ...
    ]
事件名 = eid，ts 为毫秒时间戳。
"""

import json
import re

# 匹配 "reportEvents: [" 开头的 JSON 数组（DOTALL 支持跨行）
_REPORT_RE = re.compile(r"reportEvents\s*:\s*(\[[\s\S]*\])")


def _strip_logcat_prefix(line: str) -> tuple[str, str]:
    """去掉 logcat 前缀（日期 时间 pid tid 级别 TAG:），返回 (TAG, 内容)。

    例如: "08-12 10:00:00.000 1234 1234 D hk3: message" -> ("hk3", "message")
    兼容 Samsung/Android16：logcat 的 -s tag 过滤可能失效，需本地按 tag 过滤，
    且 reportEvents 数组的每一行（含 JSON 续行）都是独立的带 tag 前缀的 logcat 行。
    """
    m = re.match(r"^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+\S+\s+\S+\s+\S+\s+(\S+):\s*(.*)$", line)
    if m:
        return m.group(1), m.group(2)
    return "", line


def _clean_line(msg: str) -> str:
    """去掉应用自带的每行自定义前缀，只保留 JSON 片段。

    真实埋点日志（如 tag=EM）每行格式：
        <空白>: <固定前缀>: reportEvents: [
        <空白>: <固定前缀>:     {
        <空白>: <固定前缀>:         "ts": 1788857691840,
    Android Studio 里固定前缀显示为 ''（adb 输出为乱码 ʼˈˉ）。
    起始行保留 reportEvents 标记；数据行从第一个 JSON 结构字符（{ } [ ] "）开始截取。
    """
    if "reportEvents" in msg:
        i = msg.find("reportEvents")
        return msg[i:]
    m = re.search(r'[\[{\]}"]', msg)
    if m:
        return msg[m.start():]
    return ""


class ReportBuffer:
    """累积多行日志，直到提取到完整 JSON 数组。"""

    def __init__(self):
        self.buf = ""
        self.in_progress = False  # 是否正在累积未闭合的 reportEvents 数组

    def feed(self, line: str) -> list[dict]:
        """输入一行原始日志，返回解析出的事件列表（可能为空）。

        兼容两种 logcat 行为：
        - 标准（Pixel 等）：多行 JSON 只有首行带 tag 前缀，续行无前缀
        - Samsung/Android16：每一行（含 JSON 续行）都带独立 tag 前缀
        """
        _, msg = _strip_logcat_prefix(line)
        msg = _clean_line(msg)
        events: list[dict] = []
        if msg:
            if "reportEvents" in msg:
                # 可能当前行就含完整数组（单行压缩 JSON）
                m = _REPORT_RE.search(msg)
                if m:
                    arr = self._try_parse(m.group(1))
                    if arr is not None:
                        events = arr
                        self.buf = ""
                    else:
                        self.buf = msg
                        events = self._try_flush()
                else:
                    # 未闭合，开始累积
                    self.buf = msg
                    events = self._try_flush()
            elif self.buf:
                self.buf += "\n" + msg
                events = self._try_flush()
        self.in_progress = bool(self.buf)
        return events

    def _try_flush(self) -> list[dict]:
        m = _REPORT_RE.search(self.buf)
        if not m:
            # 缓冲过大且无匹配则清空，避免内存膨胀
            if len(self.buf) > 200000:
                self.buf = ""
            return []
        arr = self._try_parse(m.group(1))
        if arr is not None:
            self.buf = ""
            return arr
        # 尝试闭合：若已出现 "]} 结尾但解析失败则丢弃
        if re.search(r"\]\s*$", self.buf) and "eid" in self.buf:
            self.buf = ""
        return []

    @staticmethod
    def _try_parse(text: str):
        try:
            data = json.loads(text)
        except Exception:
            return None
        if not isinstance(data, list):
            return None
        out = []
        for it in data:
            if not isinstance(it, dict):
                continue
            eid = it.get("eid")
            if not eid:
                continue
            ts = it.get("ts", 0)
            out.append({"eid": str(eid), "ts": int(ts) if isinstance(ts, (int, float)) else 0})
        return out
