import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMClientError(Exception):
    pass


class LLMClient:
    """OpenAI-compatible client via TrueFoundry gateway (Groq provider)."""

    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv(
            "LLM_BASE_URL", "https://truefoundry.prodigaltech.com/api/llm"
        )
        self.model = os.getenv("LLM_MODEL", "prodigal-groq/gpt-oss-120b")

        if not self.api_key:
            raise LLMClientError(
                "LLM_API_KEY is missing. Add it to server/.env (see .env.example)."
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_text(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a resume formatting assistant for IIT Bombay resumes. "
                            "Follow the user prompt exactly. When JSON is requested, return "
                            "valid JSON only with no markdown fences or extra commentary."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                temperature=0.2,
                extra_headers={
                    "X-TFY-METADATA": "{}",
                    "X-TFY-LOGGING-CONFIG": '{"enabled": true}',
                },
            )

            if not response.choices or not response.choices[0].message.content:
                raise LLMClientError("LLM returned an empty response.")

            return response.choices[0].message.content.strip()

        except LLMClientError:
            raise
        except Exception as error:
            raise LLMClientError(f"LLM API call failed: {error}") from error

    def generate_json(self, prompt: str):
        raw_text = self.generate_text(prompt)
        cleaned_text = self._clean_json_text(raw_text)

        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as error:
            raise LLMClientError(
                f"LLM returned invalid JSON.\n\nRaw response:\n{raw_text}\n\nError:\n{error}"
            ) from error

    @staticmethod
    def _clean_json_text(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        if text.startswith("```"):
            text = text[len("```"):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        return text


GeminiLLMClient = LLMClient
