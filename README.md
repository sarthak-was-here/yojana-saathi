# 🧭 Yojana Saathi — Agentic Government Scheme Navigator

**Discover government welfare schemes through a simple conversation.**

Yojana Saathi is an agentic AI assistant that helps citizens discover government schemes they may qualify for. It supports Hindi, English and Hinglish text or voice input, builds a structured user profile, evaluates eligibility using a deterministic rule engine, and provides personalised application guidance.

## Features

- **Multilingual interaction:** Chat in Hindi, English or Hinglish.
- **Voice input:** Describe your situation by speaking.
- **Automatic profile extraction:** Extracts information such as age, state, occupation, income and social category from natural language.
- **Eligibility engine:** Evaluates 23 curated schemes using rule-based eligibility criteria and three-valued logic.
- **Smart follow-up questions:** Identifies missing information that could affect eligibility.
- **Scheme details:** View benefits, required documents, application steps and official links.
- **Agent reasoning trace:** Inspect the tools called by the agent and their results.
- **Privacy-conscious design:** The app does not ask users for Aadhaar numbers, OTPs or passwords.

## Technology Stack

- Python 3
- Google Gemini via the `google-genai` SDK
- Streamlit
- JSON-based scheme knowledge base
- Custom Python eligibility engine

## Run Locally

### 1. Clone the repository

Replace `YOUR-USERNAME` with your GitHub username.

```bash
git clone https://github.com/YOUR-USERNAME/yojana-saathi.git
cd yojana-saathi
```

### 2. Create a virtual environment

**Windows — PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure your Gemini API key

Get an API key from [Google AI Studio](https://aistudio.google.com/apikey).

Create a `.streamlit` folder in the project root and create a file named `secrets.toml` inside it.

Your file structure should look like this:

```text
yojana-saathi/
├── .streamlit/
│   └── secrets.toml
├── app.py
├── agent.py
├── eval_engine.py
├── schemes.json
├── requirements.txt
└── README.md
```

Add the following to `.streamlit/secrets.toml`, replacing the placeholder with your own key:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "gemini-2.5-flash"
```

**Security:** Never commit or upload `secrets.toml` or your actual API key to GitHub. The repository's `.gitignore` is configured to exclude the local secrets file.

### 4. Start the application

**Windows — PowerShell**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

**macOS / Linux**

```bash
python -m streamlit run app.py
```

Open the local URL printed in the terminal, usually `http://localhost:8501`.

## Test the Eligibility Engine

The eligibility engine can be tested without making Gemini API calls.

**Windows — PowerShell**

```powershell
.\.venv\Scripts\python.exe eval_engine.py
```

**macOS / Linux**

```bash
python eval_engine.py
```

The current offline test suite contains 12 eligibility test cases and is expected to report **12/12 passing**.

## Troubleshooting

| Problem | What to do |
|---|---|
| API key or authentication error | Check that `.streamlit/secrets.toml` exists and contains a valid `GEMINI_API_KEY`. |
| Model not found / 404 | Check the configured `GEMINI_MODEL` against the [Gemini models documentation](https://ai.google.dev/gemini-api/docs/models). |
| 429 / rate limit | Gemini quotas depend on the model and API project. Wait before retrying and check your [API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). Agent tool use may consume multiple model requests per turn. |
| Microphone input unavailable | Check your Streamlit version and browser microphone permissions. Text input remains available. |
| `ModuleNotFoundError` | Activate the project's virtual environment and reinstall the packages from `requirements.txt`. |

## Project Structure

- `app.py` — Streamlit interface, chat, profile card and matched-scheme dashboard.
- `agent.py` — Gemini tool-calling agent, profile management and deterministic eligibility logic.
- `eval_engine.py` — Offline eligibility test suite.
- `schemes.json` — Structured knowledge base containing 23 curated government schemes.
- `requirements.txt` — Python dependencies.
- `.streamlit/secrets.toml` — Local API credentials; **not committed to GitHub**.

## Limitations

- The prototype covers 23 curated schemes; it does not cover every central or state scheme.
- Eligibility results are indicative and must be confirmed through the relevant official portal.
- Scheme rules and benefits can change over time.
- Gemini API availability and usage depend on the configured project's limits.
- The prototype provides guidance but does not submit applications on the user's behalf.

## Future Scope

- Expand coverage to more central and state government schemes.
- Add more Indian languages and spoken responses.
- Introduce document completeness checks with user consent.
- Explore WhatsApp, Android, IVR and Common Service Centre integrations.
- Add official-source verification and application deadline reminders.

---

**Yojana Saathi — Making welfare easier to discover, understand, and access.**