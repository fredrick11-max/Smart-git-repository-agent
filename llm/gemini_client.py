"""Thin wrapper around the Google Gemini API. It never raises: errors are returned in the result."""
from dataclasses import dataclass
from typing import Optional

from backend import config


@dataclass
class GeminiResult:
    text: Optional[str] = None
    error: Optional[str] = None
    quota_exceeded: bool = False

    @property
    def ok(self) -> bool:
        return self.text is not None and self.error is None


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = config.get_gemini_key() if api_key is None else api_key
        self.model = model or config.get_gemini_model()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, json_mode: bool = False) -> GeminiResult:
        if not self.available:
            return GeminiResult(error="No Gemini API key found. Add GEMINI_API_KEY to your .env file.")
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return GeminiResult(error="The 'google-genai' package is not installed (pip install -r requirements.txt).")
        try:
            client = genai.Client(api_key=self.api_key)
            settings = {"temperature": 0.3}
            if json_mode:
                settings["response_mime_type"] = "application/json"
            response = client.models.generate_content(
                model=self.model, contents=prompt, config=types.GenerateContentConfig(**settings)
            )
            text = (response.text or "").strip()
            if not text:
                return GeminiResult(error="Gemini returned an empty response.")
            return GeminiResult(text=text)
        except Exception as exc:
            return self._friendly_error(exc)

    @staticmethod
    def _friendly_error(exc: Exception) -> GeminiResult:
        text = str(exc)
        lowered = text.lower()
        if "429" in text or "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered:
            return GeminiResult(
                error="Gemini free-tier quota or rate limit exceeded. Wait a minute (or until tomorrow) and try again.",
                quota_exceeded=True,
            )
        if "api key" in lowered or "api_key" in lowered or "401" in text or "403" in text or "permission" in lowered:
            return GeminiResult(error="Gemini rejected the API key. Check GEMINI_API_KEY in your .env file.")
        if "404" in text or "not found" in lowered:
            return GeminiResult(error=f"Gemini model not found. Check GEMINI_MODEL in .env. ({text[:150]})")
        return GeminiResult(error=f"Gemini request failed: {text[:200]}")
