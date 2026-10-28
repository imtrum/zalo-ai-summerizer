
from google import genai
from google.genai import types

from zalo_ai.config import settings


class GeminiProvider:
    """Generate text using the Google Gemini API."""


    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is missing. "
                "Please configure it in your .env file."
            )

        if not settings.AI_MODEL:
            raise ValueError(
                "AI_MODEL is missing. "
                "Please configure it in your .env file."
            )

        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )



    def generate(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the generated text."""
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        response = self.client.models.generate_content(
            model=settings.AI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=settings.AI_TEMPERATURE,
                max_output_tokens=settings.AI_MAX_TOKENS,
            ),
        )

        if response.text is None:
            raise RuntimeError(
                "Gemini returned no text. "
                "The response may have been blocked or empty."
            )

        if response.candidates:
            finish_reason = response.candidates[0].finish_reason

            if finish_reason == types.FinishReason.MAX_TOKENS:
                raise RuntimeError(
                    "Gemini summary was truncated because it reached "
                    "the output-token limit. Increase AI_MAX_TOKENS "
                    "or summarize fewer messages per request."
                )

        return response.text.strip()
