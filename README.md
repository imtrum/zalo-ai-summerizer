# Zalo AI Summarizer

A local desktop app for collecting messages from selected Zalo conversations and summarizing them with Gemini.

## Start the app

From the project directory, activate your virtual environment and run:

```powershell
python scripts/ui.py
```

The first app launch creates an empty `data/targets.json` if one does not exist. In the **Targets** tab, choose **Refresh conversation list**, select conversations, and add them as targets. Zalo runs in the background when your saved session is valid; a browser window opens only if you need to sign in.

In the **Summarize** tab, enter a cutoff time in Vietnam time (`YYYY-MM-DD HH:MM`) and start summarization. The **Prompt** tab lets you edit and save the instructions used for future summaries.

## Gemini setup

Create a `.env` file in the project directory with your Gemini settings:

```dotenv
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash
AI_FALLBACK_MODELS=gemini-2.5-flash-lite
GEMINI_API_KEY=your_api_key
AI_MAX_TOKENS=2000
```

The app saves the custom prompt in `data/summarization_prompt.txt`. Both that file and `data/targets.json` are local configuration and are excluded from Git.
