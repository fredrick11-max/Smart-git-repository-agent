import json
import tempfile
import unittest

from agents.orchestrator import Orchestrator
from backend.qa import answer_question
from backend.reports import save_reports, to_markdown
from llm.gemini_client import GeminiResult
from tests.sample_data import sample_commits, sample_repo_info


class FakeGemini:
    def __init__(self, result, available=True):
        self.result, self.available, self.model = result, available, "fake"

    def generate(self, prompt, json_mode=False):
        return self.result


def run(gemini=None, use_ai=True):
    return Orchestrator(gemini).analyze_data(sample_repo_info(), sample_commits(), "memory", 100, use_ai)


class PipelineTests(unittest.TestCase):
    def test_pipeline_without_ai(self):
        result = run(use_ai=False)
        counts = result["statistics"]["category_counts"]
        self.assertEqual(counts["feature"], 2)
        self.assertEqual(counts["bug_fix"], 1)
        self.assertEqual(counts["refactoring"], 1)
        self.assertEqual(counts["documentation"], 1)
        self.assertEqual(counts["testing"], 1)
        self.assertEqual(result["statistics"]["top_files"][0]["path"], "calc.py")
        self.assertEqual(result["summary"]["generated_by"], "fallback")
        self.assertEqual([s["agent"] for s in result["workflow"]],
                         ["Commit Classifier", "Insight Analyst", "Summary Generator"])

    def test_quota_error_falls_back(self):
        quota = FakeGemini(GeminiResult(error="quota exceeded", quota_exceeded=True))
        result = run(quota)
        self.assertEqual(result["summary"]["generated_by"], "fallback")
        self.assertIn("quota", result["meta"]["ai_error"])
        self.assertTrue(result["summary"]["summary"])

    def test_gemini_json_is_used(self):
        reply = json.dumps({"summary": "A calculator.", "major_changes": ["a"], "development_insights": ["b"], "changelog": "### Features\n- x"})
        result = run(FakeGemini(GeminiResult(text=reply)))
        self.assertEqual(result["summary"]["generated_by"], "gemini")
        self.assertEqual(result["summary"]["summary"], "A calculator.")

    def test_bad_gemini_output_falls_back(self):
        result = run(FakeGemini(GeminiResult(text="not json at all")))
        self.assertEqual(result["summary"]["generated_by"], "fallback")

    def test_questions_and_reports(self):
        result = run(use_ai=False)
        answer, source = answer_question("Which files changed most frequently?", result)
        self.assertIn("calc.py", answer)
        self.assertEqual(source, "git data")
        self.assertIn("Fix division by zero", answer_question("Which bugs were fixed?", result)[0])
        self.assertIn("# Repository Report", to_markdown(result))
        with tempfile.TemporaryDirectory() as tmp:
            paths = save_reports(result, tmp)
            self.assertTrue(paths["markdown"].exists() and paths["json"].exists())
            json.loads(paths["json"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
