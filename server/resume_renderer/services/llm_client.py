import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class LLMClientError(Exception):
    """Custom error for LLM client failures."""

    def __init__(self, message="", *, code=None):
        super().__init__(message)
        self.code = code


class GeminiLLMClient:
    """Resume LLM adapter for Google Gemini."""

    def __init__(self, *, purpose="generation"):
        if purpose not in {"generation", "preprocessing"}:
            raise ValueError("Unknown resume LLM purpose")
        lite_model = os.getenv("ASSIST_MODEL", "").strip()
        if purpose == "preprocessing" and not lite_model:
            raise LLMClientError("Set ASSIST_MODEL for Lite preprocessing.")
        self.provider = os.getenv("RESUME_LLM_PROVIDER", "gemini").strip().lower()
        if self.provider != "gemini":
            raise LLMClientError("RESUME_LLM_PROVIDER must be 'gemini'.")
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = os.getenv("GOOGLE_MODEL") or os.getenv(
            "GEMINI_MODEL", "gemini-2.0-flash"
        )
        if purpose == "preprocessing":
            self.model = lite_model

        if not self.api_key:
            raise LLMClientError(
                "GEMINI_API_KEY or GOOGLE_API_KEY is missing. "
                "Add a Google AI Studio API key to your .env file."
            )

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

        except LLMClientError:
            raise
        except Exception as error:
            raise LLMClientError(
                self._provider_error_message(error),
                code=self._error_code(error),
            ) from error

    def generate_json(self, prompt, response_schema=None):
        try:
            gemini_schema = self._gemini_schema_format(response_schema)
            config = types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=gemini_schema,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            response_text = response.text

            if not response_text:
                raise LLMClientError("The LLM returned an empty response.")

            cleaned_text = self._clean_json_text(response_text)

            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as error:
                raise LLMClientError(f"The LLM returned invalid JSON: {str(error)}")

        except LLMClientError:
            raise

        except Exception as error:
            raise LLMClientError(
                self._provider_error_message(error),
                code=self._error_code(error),
            ) from error

    @staticmethod
    def _error_code(error):
        return getattr(error, "status_code", None) or getattr(error, "code", None)

    def _provider_error_message(self, error):
        return f"Gemini API call failed: {str(error)}"

    @staticmethod
    def _gemini_schema_format(response_schema):
        if response_schema is None:
            return None
        return GeminiLLMClient._drop_additional_properties(response_schema)

    @staticmethod
    def _drop_additional_properties(schema):
        if isinstance(schema, dict):
            result = {}
            for key, value in schema.items():
                if key == "additionalProperties":
                    continue
                result[key] = GeminiLLMClient._drop_additional_properties(value)
            return result
        if isinstance(schema, list):
            return [
                GeminiLLMClient._drop_additional_properties(item) for item in schema
            ]
        return schema

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
                    part = part[len("json") :].strip()
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
