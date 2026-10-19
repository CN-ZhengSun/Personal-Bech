import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from fastapi.params import Form

from app.api.v1 import adbtools


class DeviceFilePushTest(unittest.TestCase):
    def test_push_uses_selected_directory_and_cleans_temporary_file(self):
        pushed = {}

        def fake_run(args, timeout):
            pushed["args"] = args
            with open(args[4], "rb") as source:
                pushed["content"] = source.read()
            return SimpleNamespace(returncode=0, stdout="1 file pushed", stderr="")

        file = UploadFile(file=io.BytesIO(b"device payload"), filename="report.txt")
        with patch.object(adbtools, "_require_device"), patch.object(adbtools, "_run", side_effect=fake_run):
            result = adbtools.device_fs_push("device-1", "/sdcard/reports", file)

        self.assertTrue(result["ok"])
        self.assertEqual("device payload", pushed["content"].decode())
        self.assertEqual("/sdcard/reports/report.txt", pushed["args"][5])
        self.assertFalse(os.path.exists(pushed["args"][4]))

    def test_path_is_a_multipart_form_field(self):
        route = next(r for r in adbtools.router.routes if r.path.endswith("/fs/push"))
        path_field = next(f for f in route.dependant.body_params if f.name == "path")
        self.assertIsInstance(path_field.field_info, Form)

    def test_rejects_traversal_without_running_adb(self):
        file = UploadFile(file=io.BytesIO(b"data"), filename="report.txt")
        with patch.object(adbtools, "_require_device"), patch.object(adbtools, "_run") as run:
            with self.assertRaises(HTTPException):
                adbtools.device_fs_push("device-1", "/sdcard/../private", file)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
