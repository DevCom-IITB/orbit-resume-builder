# ==============================================================================
# ORIGINAL TRUEFOUNDRY CLIENT (COMMENTED OUT)
# ==============================================================================
# import json
# import os
# 
# from dotenv import load_dotenv
# from openai import OpenAI
# 
# load_dotenv()
# 
# 
# class LLMClientError(Exception):
#     """Custom error for LLM client failures."""
# 
#     pass
# 
# 
# class LLMClient:
#     """OpenAI-compatible client (TrueFoundry / Prodigal) for resume section generation."""
# 
#     def __init__(self):
#         self.api_key = os.getenv("LLM_API_KEY")
#         self.base_url = os.getenv(
#             "LLM_BASE_URL", "https://truefoundry.prodigaltech.com/api/llm"
#         )
#         self.model = os.getenv("LLM_MODEL", "prodigal-groq/gpt-oss-120b")
# 
#         if not self.api_key:
#             raise LLMClientError(
#                 "LLM_API_KEY is missing. Add it to server/.env (see .env.example)."
#             )
# 
#         self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
# 
#     def generate_text(self, prompt: str) -> str:
#         try:
#             response = self.client.chat.completions.create(
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": (
#                             "You are a resume formatting assistant for IIT Bombay resumes. "
#                             "Follow the user prompt exactly. When JSON is requested, return "
#                             "valid JSON only with no markdown fences or extra commentary."
#                         ),
#                     },
#                     {"role": "user", "content": prompt},
#                 ],
#                 model=self.model,
#                 temperature=0.2,
#                 extra_headers={
#                     "X-TFY-METADATA": "{}",
#                     "X-TFY-LOGGING-CONFIG": '{"enabled": true}',
#                 },
#             )
# 
#             if (
#                 not response.choices
#                 or not response.choices[0].message.content
#             ):
#                 raise LLMClientError("LLM returned an empty response.")
# 
#             return response.choices[0].message.content.strip()
# 
#         except LLMClientError:
#             raise
#         except Exception as error:
#             raise LLMClientError(f"LLM API call failed: {error}") from error
# 
#     def generate_json(self, prompt: str):
#         raw_text = self.generate_text(prompt)
#         cleaned_text = self._clean_json_text(raw_text)
# 
#         try:
#             return json.loads(cleaned_text)
#         except json.JSONDecodeError as error:
#             raise LLMClientError(
#                 f"LLM returned invalid JSON.\n\nRaw response:\n{raw_text}\n\nError:\n{error}"
#             ) from error
# 
#     @staticmethod
#     def _clean_json_text(text: str) -> str:
#         text = text.strip()
#         if text.startswith("```json"):
#             text = text[len("```json") :].strip()
# 
#         if text.startswith("```"):
#             text = text[len("```") :].strip()
# 
#         if text.endswith("```"):
#             text = text[:-3].strip()
#         return text
# 
# 
# # Backward-compatible alias used in older imports/tests.
# GeminiLLMClient = LLMClient
# ==============================================================================

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClientError(Exception):
    """Custom error for LLM client failures."""

    pass


class LLMClient:
    """BharatCode LLM client for resume section generation."""

    def __init__(self):
        self.api_key = os.getenv("BHARATCODE_API_KEY", os.getenv("LLM_API_KEY", ""))
        self.endpoint = os.getenv(
            "BHARATCODE_ENDPOINT", "https://bharatcode.ai/api/model/v1/chat/completions"
        )
        self.model = os.getenv("BHARATCODE_MODEL", "bharatcode:qwen36-35b-awq-200k")

        if not self.api_key:
            raise LLMClientError(
                "BHARATCODE_API_KEY (or LLM_API_KEY) is missing. Add it to server/.env."
            )

    def generate_text(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
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
            "temperature": 0.2,
        }

        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            response_json = response.json()
            if (
                "choices" not in response_json
                or not response_json["choices"]
                or "message" not in response_json["choices"][0]
                or not response_json["choices"][0]["message"].get("content")
            ):
                raise LLMClientError("LLM returned an empty response.")

            return response_json["choices"][0]["message"]["content"].strip()

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
            text = text[len("```json") :].strip()

        if text.startswith("```"):
            text = text[len("```") :].strip()

        if text.endswith("```"):
            text = text[:-3].strip()
        return text


# Backward-compatible alias used in older imports/tests.
GeminiLLMClient = LLMClient

