# Yojana Saathi - Agentic Government Scheme Navigator

## Run it (5 minutes)

```bash
cd yojana-saathi
python -m venv venv
# Windows:  venv\Scripts\activate        Mac/Linux:  source venv/bin/activate
pip install -r requirements.txt

# set your free Gemini key (get it at https://aistudio.google.com/apikey)
# Windows (cmd):   set GEMINI_API_KEY=your_key
# Windows (PS):    $env:GEMINI_API_KEY="your_key"
# Mac/Linux:       export GEMINI_API_KEY=your_key

streamlit run app.py
```
You can also just paste the key in the sidebar once the app opens.

## Test without an API key
```bash
python eval_engine.py     # 12 eligibility test cases, should print 12/12 passed
```

## Troubleshooting
| Problem | Fix |
|---|---|
| "model not found" / 404 | Change the model name in the sidebar to the latest Gemini Flash model listed at https://ai.google.dev/gemini-api/docs/models |
| 429 / rate limit | Free tier limit. Wait ~1 minute. Each user message uses ~3 API calls. |
| Mic button missing | Upgrade Streamlit: `pip install -U streamlit` (needs 1.40+). Typing still works. |
| `ModuleNotFoundError: google` | `pip install -U google-genai` |

## Files
- `app.py` - Streamlit UI (chat, profile card, matched-scheme cards, reasoning trace, voice input)
- `agent.py` - eligibility engine + Gemini agent with 3 tools
- `schemes.json` - knowledge base of 23 schemes with machine-readable rules
- `eval_engine.py` - offline test suite
