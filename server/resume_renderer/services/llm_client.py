import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class LLMClientError(Exception):
    """Custom error for LLM client failures."""

    pass


class GeminiLLMClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

        if not self.api_key:
            raise LLMClientError("GEMINI_API_KEY is missing. Add it to your .env file.")

        self.client = genai.Client(api_key=self.api_key)

    def generate_text(self, prompt):
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
            )

            if not response.text:
                raise LLMClientError("Gemini returned an empty response.")

            return response.text.strip()

        except Exception as error:
            raise LLMClientError(f"Gemini API call failed: {str(error)}")

    def generate_json(self, prompt):
        raw_text = self.generate_text(prompt)
        cleaned_text = self._clean_json_text(raw_text)

        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as error:
            raise LLMClientError(
                f"Gemini returned invalid JSON.\n\nRaw response:\n{raw_text}\n\nError:\n{str(error)}"
            )

    @staticmethod
    def _clean_json_text(text):
        text = text.strip()

        # Handle fenced blocks even if Gemini adds a sentence before/after them
        # e.g. "Here's the JSON:\n```json\n{...}\n```\nLet me know if you need changes."
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[len("json"):].strip()
                if part.startswith("{") or part.startswith("["):
                    return part

        # No fences: fall back to grabbing the outermost JSON object/array,
        # in case the model added any stray preamble/trailing text.
        start_candidates = [i for i in (text.find("{"), text.find("[")) if i != -1]
        if start_candidates:
            start = min(start_candidates)
            end_char = "}" if text[start] == "{" else "]"
            end = text.rfind(end_char)
            if end != -1 and end > start:
                return text[start : end + 1].strip()

        return text