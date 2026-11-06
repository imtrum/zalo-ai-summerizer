# Zalo AI Summarizer

A local desktop app for collecting messages from selected Zalo conversations and summarizing them with Gemini.

## Start the app

From the project directory, activate your virtual environment and run:

```powershell
python scripts/ui.py
```

After installing the project, the console command is also available:

```powershell
zalo-ai-summarizer
```

The first app launch creates an empty data/targets.json if one does not exist. In the Targets tab, choose Refresh conversation list, select conversations, and add them as targets. Zalo runs in the background when your saved session is valid; a browser window opens only if you need to sign in.

In the Summarize tab, choose the cutoff date and time in Vietnam time, then start summarization. The Prompt tab lets you edit and save the instructions used for future summaries.

## Gemini setup

Create a .env file in the project directory with your Gemini settings:

```dotenv
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash
AI_FALLBACK_MODELS=gemini-2.5-flash-lite
GEMINI_API_KEY=your_api_key
AI_MAX_TOKENS=2000
```

The app saves the custom prompt in data/summarization_prompt.txt. Both that file and data/targets.json are local configuration and are excluded from Git.

## Code layout

- src/zalo_ai/ui/ contains the desktop app shell, shared theme, and individual tabs.
- src/zalo_ai/workflows/ coordinates summarization and target-refresh flows; the existing zalo_ai.workflows public imports remain available.
- src/zalo_ai/integrations/zalo/ contains Zalo browser, conversation, selector, message collection, parsing, and scrolling code.
- src/zalo_ai/ai/, config/, models/, summarizer/, and targets/ contain provider, configuration, data, and summarization logic. Compatibility modules preserve former Zalo collector and discovery imports.
- src/zalo_ai/paths.py anchors project data, browser-session, prompt, and log paths to the project root.
- scripts/zalo_diagnostics/ contains manual diagnostics, while scripts/examples/ contains runnable demonstrations. Use discover_conversations.py, run_batch_pipeline_demo.py, and run_gemini_summarization_demo.py for the renamed manual commands. The prior test_* script launchers remain available for compatibility.
- tests/ groups automated tests by domain, and tests/fixtures/ contains committed sample input data.

Runtime files such as .env, data/targets.json, data/summarization_prompt.txt, data/browser_profile/, and logs/ remain rooted at the project directory and are excluded from Git.
