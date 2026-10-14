
class MockProvider:
    """Return a fixed response for local testing."""

    def generate(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        return "[MOCK SUMMARY] This is a test summary."