import unittest

from agents.commit_classifier import classify_commit
from tests.sample_data import make_commit


class ClassifierTests(unittest.TestCase):
    def check(self, message, files, expected, **kw):
        result = classify_commit(make_commit(1, message, files, **kw))
        self.assertEqual(result["category"], expected, result)

    def test_feature(self):
        self.check("Add multiply and divide functions", [("calc.py", 8, 0)], "feature")

    def test_bug_fix(self):
        self.check("Fix division by zero crash", [("calc.py", 3, 1)], "bug_fix")

    def test_refactoring(self):
        self.check("Refactor calculator: extract helper", [("calc.py", 20, 15)], "refactoring")

    def test_documentation_by_path_beats_fix_word(self):
        self.check("Fix typo in README", [("README.md", 1, 1)], "documentation")

    def test_testing(self):
        self.check("Add unit tests", [("tests/test_calc.py", 12, 0)], "testing")

    def test_conventional_prefix(self):
        self.check("fix(api): handle None", [("api.py", 2, 1)], "bug_fix")

    def test_unknown_is_other(self):
        self.check("Bump version", [("version.txt", 1, 1)], "other")

    def test_diff_evidence_without_keywords(self):
        self.check("Tidy calculator", [("calc.py", 6, 6)], "refactoring")


if __name__ == "__main__":
    unittest.main()
