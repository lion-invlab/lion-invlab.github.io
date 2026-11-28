import json
import tempfile
import unittest
from pathlib import Path

from run_stage5 import write_state_json


class Stage5StatePersistenceTests(unittest.TestCase):
    def test_running_state_is_written_as_parseable_json(self):
        state = {
            "state_version": 2,
            "stages": {"STAGE_5": {"status": "RUNNING"}},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run-state.json"
            write_state_json(path, state)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), state)
            self.assertTrue(path.read_bytes().endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
