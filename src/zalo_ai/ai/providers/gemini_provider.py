import logging
import time

from google import genai
from google.genai import types

from zalo_ai.config import settings

logger = logging.getLogger(__name__)

# Seconds to wait before each retry when a model is busy (HTTP 503).
RETRY_DELAYS = (5, 10)
# HTTP codes meaning "this model can't serve us right now": try the next one.
FALLBACK_CODES = {429, 503}


class GeminiProviderError(RuntimeError):
    """A handled failure while requesting a Gemini response."""


class _TryNextModel(Exception):
    """The current model is unusable for this request; fall back."""


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

        self.models = tuple(dict.fromkeys(
            model.strip()
            for model in (settings.AI_MODEL, *settings.AI_FALLBACK_MODELS)
            if model.strip()
        ))
        self._start = 0  # stay on a fallback model once we had to switch
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate(self, prompt: str) -> str:
        """Generate text, retrying busy models and falling back if needed."""
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        last_error = ""
        for index in range(self._start, len(self.models)):
            try:
                text = self._request(self.models[index], prompt)
            except _TryNextModel as exc:
                last_error = str(exc)
                logger.warning("%s Trying the next model.", exc)
                continue
            self._start = index
            return text

        raise GeminiProviderError(
            f"All configured Gemini models failed. Last error: {last_error}"
        )

    def _request(self, model: str, prompt: str) -> str:
        """Query one model. Raise _TryNextModel if another model may work."""
        for attempt, delay in enumerate((*RETRY_DELAYS, None)):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=settings.AI_TEMPERATURE,
                        max_output_tokens=settings.AI_MAX_TOKENS,
                    ),
                )
                break
            except Exception as exc:
                code = getattr(exc, "code", None)  # set by genai APIError
                if code == 503 and delay is not None:
                    logger.warning(
                        "Gemini '%s' is busy. Retrying in %ss...", model, delay
                    )
                    time.sleep(delay)
                    continue
                message = f"'{model}' failed: {type(exc).__name__}: {exc}"
                if code in FALLBACK_CODES:
                    raise _TryNextModel(f"Gemini model {message}") from exc
                raise GeminiProviderError(f"Gemini request {message}") from exc

        logger.info(
            "Gemini tokens: model=%s total=%s",
            model,
            getattr(response.usage_metadata, "total_token_count", None),
        )

        text = (response.text or "").strip()
        if not text:
            finish_reasons = [
                str(candidate.finish_reason)
                for candidate in response.candidates or []
            ]
            raise _TryNextModel(
                f"Gemini returned no text from model '{model}' "
                f"(prompt_feedback={response.prompt_feedback!r}, "
                f"finish_reasons={finish_reasons})."
            )

        if (
            response.candidates
            and response.candidates[0].finish_reason
            == types.FinishReason.MAX_TOKENS
        ):
            raise GeminiProviderError(
                f"Gemini model '{model}' summary was truncated at the "
                "output-token limit. Increase AI_MAX_TOKENS or summarize "
                "fewer messages per request."
            )
        return text