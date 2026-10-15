# SignalSort

AI-powered customer feedback intelligence. Paste reviews, support tickets or interview
notes and get:

- a concise overall summary
- recurring themes, each with sentiment and an estimated prevalence
- verbatim evidence quotes, **checked against your input**
- prioritised (P1/P2/P3), actionable recommendations
- Markdown and CSV export

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set ANTHROPIC_API_KEY
streamlit run app.py
```

Without an API key the app still runs: it explains that AI analysis isn't configured and
offers a clearly labelled, hand-written example report for the sample dataset.

### Tests

```bash
pip install pytest
python -m pytest -q
```

The tests use a fake LLM client and Streamlit's headless `AppTest`, so they need no API
key and make no network calls.

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes, for live analysis | Read server-side from `.env` locally or from Streamlit secrets when deployed. Never sent to the browser. |
| `SIGNALSORT_MODEL` | No | Overrides the model (default `claude-opus-5-5`). |

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. On share.streamlit.io, create an app from the repo with `app.py` as the entry point.
3. In **Advanced settings → Secrets**, add `ANTHROPIC_API_KEY = "..."`.
4. Set a monthly spend limit on the API key: the app has no login, and the
   per-session run cap (10) is only a soft guard.

## How it works

```
app.py (Streamlit UI) → analyzer.analyse() → one Claude call with a JSON schema
                                        ↓
                    Pydantic validation (models.py) → quote grounding → UI / export
```

- **One structured call.** The model's reply is constrained to the JSON schema generated from
  `models.Analysis` and validated with Pydantic. If validation fails, the call is retried once.
- **Quote grounding.** Every evidence quote is checked against the input after normalising
  case, whitespace and typographic quotes/dashes. Quotes that don't match are removed
  and the UI says how many were dropped. Themes left without evidence are flagged.
- **No invented numbers.** Prevalence is a high/medium/low *estimate* and is labelled as one.
  The app doesn't show exact counts because it doesn't count mentions.
- **Untrusted input.** Feedback is wrapped in `<feedback>` tags and the model is told to treat
  it as data, not instructions. Rendered text is escaped so `$`, `*`, etc. display literally.

| File | Role |
|---|---|
| `app.py` | Streamlit UI and session state |
| `analyzer.py` | Input checks, prompt, API call, error mapping, quote grounding |
| `models.py` | Pydantic schema shared by the prompt and the validator |
| `report.py` | Markdown and CSV export |
| `samples.py` | Sample dataset (fictional app "Trackly") and hand-written example report |

## Known limitations

- Input is capped at 30,000 characters per analysis, with no chunking for larger datasets.
- Quote matching ignores case and whitespace, so a displayed quote may differ from the
  source in capitalisation only.
- No accounts, history or storage: results live in the browser session only.
