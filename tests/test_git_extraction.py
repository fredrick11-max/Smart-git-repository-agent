"""Needs GitPython and the git program. Skipped automatically when GitPython is not installed."""
import tempfile
import unittest
from pathlib import Path

try:
    import git
    HAVE_GIT = True
except ImportError:
    HAVE_GIT = False


@unittest.skipUnless(HAVE_GIT, "GitPython is not installed")
class GitExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from examples.create_sample_repo import create_sample_repo
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = create_sample_repo(Path(cls.tmp.name) / "repo")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.tmp.cleanup()
        except OSError:
            pass

    def test_extract_real_commits(self):
        from backend.extractor import extract_commits
        from git import Repo
        commits = extract_commits(Repo(str(self.path)), 50)
        self.assertEqual(len(commits), 6)
        self.assertEqual(commits[0]["message"], "Add README with usage instructions")
        self.assertEqual({c["author"] for c in commits}, {"Alice Dev", "Bob Coder"})
        self.assertTrue(all(c["files"] for c in commits))

    def test_full_pipeline_on_sample_repo(self):
        from agents.orchestrator import Orchestrator
        result = Orchestrator().run(str(self.path), 50, use_ai=False)
        counts = result["statistics"]["category_counts"]
        self.assertEqual((counts["feature"], counts["bug_fix"], counts["refactoring"], counts["documentation"], counts["testing"]),
                         (2, 1, 1, 1, 1))
        self.assertGreaterEqual(result["repository"]["branch_count"], 2)

    def test_invalid_path(self):
        from backend.errors import RepositoryError
        from backend.git_utils import open_repository
        with self.assertRaises(RepositoryError):
            open_repository(str(Path(self.tmp.name) / "does-not-exist"))


if __name__ == "__main__":
    unittest.main()
