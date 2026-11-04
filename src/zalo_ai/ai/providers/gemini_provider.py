import time

from google import genai
from google.genai import errors, types

from zalo_ai.config import settings


class GeminiProviderError(RuntimeError):
    """A handled failure while requesting a Gemini response."""


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

        configured_models = [
            settings.AI_MODEL,
            *settings.AI_FALLBACK_MODELS,
        ]
        self.models = tuple(dict.fromkeys(
            model.strip()
            for model in configured_models
            if model.strip()
        ))
        self.active_model_index = 0

        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    @staticmethod
    def _log_usage(model: str, response) -> None:
        usage = response.usage_metadata
        if usage is not None:
            print(
                f"[Gemini tokens] model={model} "
                f"total={usage.total_token_count or 0}"
            )
        else:
            print(f"[Gemini tokens] model={model} usage unavailable")

    @staticmethod
    def _response_metadata(response) -> str:
        prompt_feedback = getattr(response, "prompt_feedback", None)
        candidate_details = []

        for candidate in response.candidates or []:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            candidate_details.append({
                "finish_reason": str(
                    getattr(candidate, "finish_reason", None)
                ),
                "safety_ratings": [
                    {
                        "category": str(
                            getattr(rating, "category", None)
                        ),
                        "probability": str(
                            getattr(rating, "probability", None)
                        ),
                        "blocked": getattr(rating, "blocked", None),
                    }
                    for rating in (
                        getattr(candidate, "safety_ratings", None) or []
                    )
                ],
                "parts": [
                    {
                        "text_length": len(part.text)
                        if isinstance(getattr(part, "text", None), str)
                        else 0,
                        "thought": getattr(part, "thought", None),
                        "has_function_call": (
                            getattr(part, "function_call", None) is not None
                        ),
                    }
                    for part in parts
                ],
            })

        return (
            f"prompt_feedback={prompt_feedback!r}; "
            f"candidates={candidate_details!r}"
        )

    def generate(self, prompt: str) -> str:
        """Generate text, retrying transient failures and switching models."""
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        print(f"Max tokens per request = {settings.AI_MAX_TOKENS}")

        response = None
        used_model = ""

        for model_index in range(
            self.active_model_index,
            len(self.models),
        ):
            model = self.models[model_index]

            for attempt in range(3):
                try:
                    candidate_response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=settings.AI_TEMPERATURE,
                            max_output_tokens=settings.AI_MAX_TOKENS,
                        ),
                    )
                except errors.APIError as exc:
                    if exc.code == 503 and attempt < 2:
                        delay = 5 * (2 ** attempt)
                        print(
                            f"Gemini model '{model}' is busy. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                        continue

                    if exc.code in {429, 503}:
                        if model_index + 1 < len(self.models):
                            next_model = self.models[model_index + 1]
                            self.active_model_index = model_index + 1
                            response = None
                            print(
                                f"Gemini model '{model}' returned "
                                f"{exc.code} ({exc.status}). "
                                f"Switching to '{next_model}'."
                            )
                            break

                        raise GeminiProviderError(
                            "All configured Gemini models failed. "
                            f"Last model '{model}' returned "
                            f"{exc.code} {exc.status}: {exc.message}"
                        ) from exc

                    raise GeminiProviderError(
                        f"Gemini request failed for model '{model}' "
                        f"({exc.code} {exc.status}): {exc.message}"
                    ) from exc

                except Exception as exc:
                    raise GeminiProviderError(
                        f"Unexpected error while requesting Gemini model "
                        f"'{model}': {type(exc).__name__}: {exc}"
                    ) from exc

                self._log_usage(model, candidate_response)
                candidate_text = candidate_response.text
                if candidate_text is None or not candidate_text.strip():
                    metadata = self._response_metadata(candidate_response)
                    print(f"[Gemini response metadata] {metadata}")

                    if model_index + 1 < len(self.models):
                        next_model = self.models[model_index + 1]
                        self.active_model_index = model_index + 1
                        response = None
                        print(
                            f"Gemini model '{model}' returned no usable text. "
                            f"Switching to '{next_model}'."
                        )
                        break

                    if attempt < 2:
                        delay = 5 * (2 ** attempt)
                        print(
                            f"Gemini model '{model}' returned no usable text. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                        continue

                    raise GeminiProviderError(
                        f"Gemini model '{model}' returned no text after "
                        f"three attempts. Response metadata: {metadata}"
                    )

                response = candidate_response
                used_model = model
                self.active_model_index = model_index
                break

            if response is not None:
                break

        if response is None:
            raise GeminiProviderError(
                "Gemini did not return a usable response from any "
                "configured model."
            )

        if response.candidates:
            finish_reason = response.candidates[0].finish_reason

            if finish_reason == types.FinishReason.MAX_TOKENS:
                raise GeminiProviderError(
                    f"Gemini model '{used_model}' summary was truncated "
                    "at the output-token limit. Increase AI_MAX_TOKENS "
                    "or summarize fewer messages per request."
                )

        return response.text.strip()
