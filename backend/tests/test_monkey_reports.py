import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api.v1 import adbtools


class MonkeyReportTest(unittest.TestCase):
    def test_run_saves_complete_log_for_preview_and_delete(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
            report_dir = Path(temp_dir) / "monkey_reports"

            def fake_run(args, stdout, stderr, timeout):
                self.assertIn("-v", args)
                self.assertIn("--pct-trackball", args)
                stdout.write(b":Sending Touch event\nMonkey finished\n")
                return SimpleNamespace(returncode=0)

            with patch.object(adbtools, "_require_device"), \
                    patch.object(adbtools, "_monkey_report_dir", return_value=report_dir), \
                    patch.object(adbtools, "_monkey_pids", return_value=[]), \
                    patch.object(adbtools.subprocess, "run", side_effect=fake_run):
                result = adbtools.device_monkey("device-1")
                reports = adbtools.list_monkey_reports("device-1")["reports"]
                self.assertTrue(result["ok"])
                self.assertEqual(1, len(reports))
                name = reports[0]["name"]
                self.assertEqual(name, result["report"]["name"])
                self.assertEqual(report_dir / name, adbtools.view_monkey_report("device-1", name).path)
                content = (report_dir / name).read_text(encoding="utf-8")
                self.assertIn(":Sending Touch event", content)
                self.assertIn("状态：退出码 0", content)
                adbtools.delete_monkey_report("device-1", name)
                self.assertEqual([], adbtools.list_monkey_reports("device-1")["reports"])

    def test_timeout_still_keeps_partial_report(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
            report_dir = Path(temp_dir)

            def fake_run(args, stdout, stderr, timeout):
                stdout.write(b"partial monkey log\n")
                raise subprocess.TimeoutExpired(args, timeout)

            with patch.object(adbtools, "_require_device"), \
                    patch.object(adbtools, "_monkey_report_dir", return_value=report_dir), \
                    patch.object(adbtools, "_monkey_pids", return_value=[]), \
                    patch.object(adbtools, "_stop_monkey_pids", return_value=[123]), \
                    patch.object(adbtools.subprocess, "run", side_effect=fake_run):
                result = adbtools.device_monkey("device-1")
                self.assertFalse(result["ok"])
                content = (report_dir / result["report"]["name"]).read_text(encoding="utf-8")
                self.assertIn("partial monkey log", content)
                self.assertIn("运行超时", content)
                self.assertIn("已停止设备上的 Monkey", content)

    def test_completed_adb_does_not_claim_success_while_device_monkey_runs(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
            with patch.object(adbtools, "_require_device"), \
                    patch.object(adbtools, "_monkey_report_dir", return_value=Path(temp_dir)), \
                    patch.object(adbtools, "_monkey_pids", side_effect=[[], [123]]), \
                    patch.object(adbtools.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
                result = adbtools.device_monkey("device-1")
                self.assertFalse(result["ok"])
                self.assertIn("仍在运行", result["output"])

    def test_status_and_stop_only_target_monkey_pid(self):
        ps = SimpleNamespace(returncode=0, stdout="PID NAME\n 123 com.android.commands.monkey\n 456 com.example.app\n")
        stopped = SimpleNamespace(returncode=0, stdout="")
        empty = SimpleNamespace(returncode=0, stdout="PID NAME\n 456 com.example.app\n")
        with patch.object(adbtools, "_require_device"), \
                patch.object(adbtools, "_run", side_effect=[ps, ps, stopped, empty, empty]) as run:
            self.assertEqual({"running": True, "pids": [123]}, adbtools.device_monkey_status("device-1"))
            self.assertEqual({"ok": True, "stopped": True, "pids": [123]}, adbtools.device_monkey_stop("device-1"))
            self.assertEqual(["adb", "-s", "device-1", "shell", "kill", "123"], run.call_args_list[2].args[0])

    def test_stop_escalates_only_confirmed_monkey_pid(self):
        with patch.object(adbtools, "_monkey_pids", side_effect=[[123], [123], [123], [123], [123], [123], [123], []]), \
                patch.object(adbtools, "_run", return_value=SimpleNamespace(returncode=0)) as run, \
                patch.object(adbtools.time, "sleep"):
            self.assertEqual([123], adbtools._stop_monkey_pids("device-1"))
            self.assertEqual(["adb", "-s", "device-1", "shell", "kill", "-9", "123"], run.call_args_list[-1].args[0])

    def test_list_creates_default_report_directory(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
            report_dir = Path(temp_dir) / "monkey_reports" / "device"
            with patch.object(adbtools, "_monkey_report_dir", return_value=report_dir):
                self.assertEqual([], adbtools.list_monkey_reports("device-1")["reports"])
                self.assertTrue(report_dir.is_dir())

    def test_delete_rejects_non_report_paths(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
            with patch.object(adbtools, "_monkey_report_dir", return_value=Path(temp_dir)):
                with self.assertRaises(HTTPException):
                    adbtools.delete_monkey_report("device-1", "../other.txt")


if __name__ == "__main__":
    unittest.main()
