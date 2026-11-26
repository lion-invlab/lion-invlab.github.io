import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_main_preview import git_blob_sha, prepare_delivery


DATE = "2026-11-26"
RUN_ID = "45731349178"
ATTEMPT = "1"
TRIGGER = "a" * 40
BRANCH = "simulation/tac-process-lab-2026-11-06"


def make_source(root: Path, *, ready=True, run_id=RUN_ID, attempt=ATTEMPT, tamper_sha=False):
    preview = root / "preview"
    preview.mkdir(parents=True, exist_ok=True)
    html = f'<!doctype html><html><head><meta name="report-date" content="{DATE}"></head><body>review</body></html>'.encode()
    html_path = preview / f"{DATE}-simulation.html"
    qa_path = preview / f"{DATE}-simulation.qa.json"
    html_path.write_bytes(html)
    qa = {
        "status": "QA_PASSED",
        "review_ready": ready,
        "data_review_ready": ready,
        "sim14_review_ready": ready,
        "sim14_builder_approval": "APPROVED",
        "branch": BRANCH,
        "report_path": f"preview/{DATE}-simulation.html",
        "report_date": DATE,
        "report_git_blob_sha": "0" * 40 if tamper_sha else git_blob_sha(html),
        "report_sha256": hashlib.sha256(html).hexdigest(),
        "workflow_run_id": str(run_id),
        "workflow_run_attempt": str(attempt),
        "prebuild_input_receipt_sha256": "b" * 64,
        "prebuild_input_receipt": {"status": "PASS"},
        "builder_blob_sha": "c" * 40,
        "builder_approval_record": {
            "decision": "APPROVED",
            "approved_builder_path": "simulation-lab/runner/build_review_html.py",
            "approved_builder_blob_sha": "c" * 40,
            "actual_builder_blob_sha": "c" * 40,
        },
        "review_ready_blockers": [],
        "sim14_blockers": [],
    }
    qa_path.write_text(json.dumps(qa), encoding="utf-8")
    return html_path, qa_path, html


class MainPreviewDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "simulation"
        self.main = self.root / "main"
        self.source.mkdir()
        self.main.mkdir()
        (self.main / "index.html").write_text("production homepage", encoding="utf-8")
        self.html_path, self.qa_path, self.html = make_source(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def test_writes_only_canonical_main_preview_files(self):
        result = prepare_delivery(self.html_path, self.qa_path, self.main, DATE, RUN_ID, ATTEMPT, TRIGGER)
        self.assertEqual(result["status"], "READY_FOR_MAIN_COMMIT")
        self.assertEqual((self.main / f"preview/{DATE}-review.html").read_bytes(), self.html)
        qa = json.loads((self.main / f"preview/{DATE}-review.qa.json").read_text())
        self.assertEqual(qa["branch"], BRANCH)
        self.assertEqual(qa["delivery_branch"], "main")
        self.assertEqual(qa["report_path"], f"preview/{DATE}-review.html")
        receipt = json.loads((self.main / f"preview/{DATE}-review.delivery.json").read_text())
        self.assertEqual(receipt["allowed_main_paths"], [
            f"preview/{DATE}-review.html",
            f"preview/{DATE}-review.qa.json",
            f"preview/{DATE}-review.delivery.json",
        ])
        self.assertEqual((self.main / "index.html").read_text(), "production homepage")
        self.assertEqual(len(list((self.main / "preview").iterdir())), 3)

    def test_rejects_non_review_ready_sidecar(self):
        self.html_path, self.qa_path, _ = make_source(self.source, ready=False)
        with self.assertRaises(SystemExit):
            prepare_delivery(self.html_path, self.qa_path, self.main, DATE, RUN_ID, ATTEMPT, TRIGGER)

    def test_rejects_wrong_run_or_attempt(self):
        with self.assertRaises(SystemExit):
            prepare_delivery(self.html_path, self.qa_path, self.main, DATE, "other-run", ATTEMPT, TRIGGER)
        with self.assertRaises(SystemExit):
            prepare_delivery(self.html_path, self.qa_path, self.main, DATE, RUN_ID, "2", TRIGGER)

    def test_rejects_html_sha_mismatch(self):
        self.html_path, self.qa_path, _ = make_source(self.source, tamper_sha=True)
        with self.assertRaises(SystemExit):
            prepare_delivery(self.html_path, self.qa_path, self.main, DATE, RUN_ID, ATTEMPT, TRIGGER)

    def test_rejects_symlinked_preview_directory(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.main / "preview").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(SystemExit):
            prepare_delivery(self.html_path, self.qa_path, self.main, DATE, RUN_ID, ATTEMPT, TRIGGER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
