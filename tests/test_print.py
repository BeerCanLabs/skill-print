"""tests.test_print: Unit tests for print_skill."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from print_skill import (
    PrintClient,
    cancel_job,
    get_health,
    list_jobs,
    list_printers,
    print_file,
    print_text,
    print_url,
)
from tests.fake_gatekeeper import TEST_RUN_TOKEN, FakeGatekeeper


class TestPrintSkill(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeGatekeeper()
        self.client = PrintClient(
            base_url=self.fake.base_url,
            run_token=TEST_RUN_TOKEN,
        )

    def tearDown(self) -> None:
        self.fake.close()

    def test_print_text_success(self) -> None:
        res = self.client.print_text("Morning Agenda:\n1. Standup\n2. Design Review", title="Morning Brief", copies=2)
        self.assertTrue(res.get("ok"))
        self.assertTrue(res.get("printed"))
        self.assertEqual(res.get("job_id"), "job-0001")

        req = self.fake.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["path"], "/print/jobs")
        self.assertEqual(req["auth"], f"Bearer {TEST_RUN_TOKEN}")
        self.assertEqual(req["body"]["kind"], "text")
        self.assertEqual(req["body"]["title"], "Morning Brief")
        self.assertEqual(req["body"]["copies"], 2)

    def test_print_text_empty_refused(self) -> None:
        res = self.client.print_text("")
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("error"), "EmptyDocument")

    def test_print_text_copies_capped(self) -> None:
        self.client.print_text("Meeting Notes", copies=10)
        req = self.fake.requests[-1]
        self.assertEqual(req["body"]["copies"], 5)

    def test_print_file_bytes(self) -> None:
        fake_pdf = b"%PDF-1.4 Fake PDF Content"
        res = self.client.print_file(fake_pdf, filename="contract.pdf", title="Contract v1")
        self.assertTrue(res.get("ok"))

        req = self.fake.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["body"]["kind"], "file")
        self.assertEqual(req["body"]["filename"], "contract.pdf")
        self.assertTrue("payload" in req["body"])

    def test_print_url(self) -> None:
        res = self.client.print_url("https://example.com/receipt.pdf", title="Receipt")
        self.assertTrue(res.get("ok"))

        req = self.fake.requests[-1]
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["body"]["kind"], "url")
        self.assertEqual(req["body"]["url"], "https://example.com/receipt.pdf")

    def test_get_health(self) -> None:
        res = self.client.get_health()
        self.assertTrue(res.get("ok"))
        self.assertTrue(res.get("house_awake"))
        self.assertEqual(res.get("default_printer"), "HP_Color_LaserJet_Pro_MFP_3301")

    def test_list_printers(self) -> None:
        res = self.client.list_printers()
        self.assertTrue(res.get("ok"))
        self.assertEqual(len(res.get("printers", [])), 2)

    def test_list_and_cancel_jobs(self) -> None:
        self.client.print_text("Task 1")
        self.client.print_text("Task 2")

        jobs_res = self.client.list_jobs()
        self.assertTrue(jobs_res.get("ok"))
        self.assertEqual(len(jobs_res.get("pending", [])), 2)

        cancel_res = self.client.cancel_job("job-0001")
        self.assertTrue(cancel_res.get("ok"))

        jobs_after = self.client.list_jobs()
        self.assertEqual(len(jobs_after.get("pending", [])), 1)

    def test_top_level_module_functions_use_env(self) -> None:
        env = {
            "PRINT_BASE_URL": self.fake.base_url,
            "FACTORY_RUN_TOKEN": TEST_RUN_TOKEN,
        }
        with patch.dict("os.environ", env):
            res = print_text("Test via top-level function")
            self.assertTrue(res.get("ok"))

            health = get_health()
            self.assertTrue(health.get("ok"))

            printers = list_printers()
            self.assertTrue(printers.get("ok"))

            jobs = list_jobs()
            self.assertTrue(jobs.get("ok"))

            cancel = cancel_job("job-0001")
            self.assertTrue(cancel.get("ok"))

    def test_runtime_tools_and_smoke_and_staged_file(self) -> None:
        import json
        import tempfile
        from pathlib import Path
        from print_skill import tools

        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "PRINT_BASE_URL": self.fake.base_url,
                "FACTORY_RUN_TOKEN": TEST_RUN_TOKEN,
                "ATTACHMENT_STAGING_DIR": tmp,
            }
            with patch.dict("os.environ", env):
                by_name = {t["name"]: t for t in tools()}
                smoke_out = json.loads(by_name["check_printer_health"]["handler"]({}, {"smoke": True}))
                self.assertTrue(smoke_out.get("ok"))

                denied = json.loads(by_name["print_file_path"]["handler"]({"local_path": "/etc/hosts"}, {}))
                self.assertFalse(denied.get("ok"))

                staged = Path(tmp) / "doc.pdf"
                staged.write_bytes(b"%PDF-1.4 test")
                printed = json.loads(by_name["print_file_path"]["handler"]({"local_path": str(staged)}, {}))
                self.assertTrue(printed.get("ok"))


if __name__ == "__main__":
    unittest.main()
