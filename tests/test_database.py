import tempfile
import unittest
from pathlib import Path

from agents.orchestrator import Orchestrator
from database.db import AnalysisDatabase
from tests.sample_data import sample_commits, sample_repo_info


class DatabaseTests(unittest.TestCase):
    def test_save_load_list_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = AnalysisDatabase(Path(tmp) / "test.db")
            analysis = Orchestrator().analyze_data(sample_repo_info(), sample_commits(), "memory", 100, use_ai=False)
            new_id = db.save_analysis(analysis)
            listing = db.list_analyses()
            self.assertEqual(len(listing), 1)
            self.assertEqual(listing[0]["commit_count"], 6)
            loaded = db.get_analysis(new_id)
            self.assertEqual(loaded["statistics"]["total_commits"], 6)
            self.assertTrue(db.delete_analysis(new_id))
            self.assertIsNone(db.get_analysis(new_id))


if __name__ == "__main__":
    unittest.main()
