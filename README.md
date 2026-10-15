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
cp .env.example .env          # then set GEMINI_API_KEY (free: https://aistudio.google.com/apikey)
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
| `GEMINI_API_KEY` | Yes, for live analysis | Free Google AI Studio key. Read server-side from `.env` locally or from Streamlit secrets when deployed. Never sent to the browser. |
| `SIGNALSORT_MODEL` | No | Overrides the model (default `gemini-3.8-flash`). |

### Free-tier trade-offs

- **Cost:** none, but Google enforces per-minute and per-day request limits. When they're hit
  the app shows a "rate limit or daily quota reached" message.
- **Reliability:** free-tier models are sometimes overloaded or out of quota. Transient server
  errors are retried up to 3 times, and if the primary model still fails with a capacity or
  quota error the app tries `gemini-3.6-flash` once. The report banner names the model that
  actually produced the analysis.
- **Privacy:** on the free tier, Google may use submitted content to improve its products.
  The app's footer says so. Switch the key to a paid Gemini plan before analysing real
  customer data.

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. On share.streamlit.io, create an app from the repo with `app.py` as the entry point.
3. In **Advanced settings → Secrets**, add `GEMINI_API_KEY = "..."`.
4. The app has no login, so anyone with the URL shares your free-tier quota. The
   per-session run cap (10) is only a soft guard.

## How it works

```
app.py (Streamlit UI) → analyzer.analyse() → one Gemini call with a JSON schema
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
