import unittest

from app.services.logcat import (
    build_log_record,
    parse_package_uid_output,
    parse_process_output,
    parse_threadtime_line,
)


class LogcatParserTest(unittest.TestCase):
    def test_parses_year_uid_tag_and_message(self):
        line = "2026-09-10 15:34:53.819 10291 13537 13537 D FirebaseSessions: App foregrounded"

        record = parse_threadtime_line(line)

        self.assertEqual("10291", record["uid"])
        self.assertEqual("13537", record["pid"])
        self.assertEqual("FirebaseSessions", record["tag"])
        self.assertEqual("App foregrounded", record["message"])

    def test_parses_legacy_threadtime_without_uid(self):
        line = "09-10 15:34 Dee 13537 13537 D Tag: message"

        self.assertIsNone(parse_threadtime_line(line))
        record = parse_threadtime_line("09-10 15:34:53.819 13537 13537 D Tag: message")

        self.assertEqual("", record["uid"])
        self.assertEqual("Tag", record["tag"])

    def test_builds_stable_package_metadata_from_uid(self):
        line = "2026-09-10 15:34:53.819 10291 13537 13537 I WorkManager: Started work"

        record = build_log_record(line, {"10291": ("com.qwe.test.test",)}, {})

        self.assertEqual("com.qwe.test.test", record["application_id"])
        self.assertEqual("com.qwe.test.test", record["process_name"])
        self.assertNotIn("com.qwe.test.test", record["raw"])

    def test_parses_package_and_process_commands(self):
        packages = parse_package_uid_output(
            "package:com.example.one uid:10123\npackage:com.example.two uid:10123\ninvalid"
        )
        processes = parse_process_output(
            "USER PID PPID VSZ RSS WCHAN ADDR S NAME\n"
            "u0_a123 4321 1 0 0 0 0 S com.example.one:remote\n"
        )

        self.assertEqual(("com.example.one", "com.example.two"), packages["10123"])
        self.assertEqual("com.example.one:remote", processes["4321"])


if __name__ == "__main__":
    unittest.main()
