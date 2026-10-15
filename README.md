# SignalSort

**Customer feedback intelligence in one paste.** SignalSort turns a pile of reviews, support
tickets or interview notes into a short, evidence-backed brief a product team can act on.

**Live app:** https://algosoupgit-xttfoqcvhnxkzanecxx9z9.streamlit.app/
(Hosted on Streamlit Community Cloud with a shared free-tier Gemini quota. If it reports a
rate-limit or overload message, wait a minute and retry.)

## The problem

Product managers, founders, customer-success leads and UX researchers sit on hundreds of
unstructured comments. Reading them all is slow, skim-reading misses patterns, and a
generic chatbot summary tends to paraphrase or invent quotes, so it can't be trusted as
evidence in a roadmap discussion.

## What it does

Paste feedback (or load the built-in sample) and get:

- a concise overall summary and overall sentiment
- recurring **themes**, each with a sentiment and an *estimated* prevalence (high / medium / low)
- **verbatim evidence quotes**, each checked against your input (see below)
- **prioritised recommendations** (P1 do now / P2 next / P3 later) linked to the themes behind them
- **Markdown and CSV export**, with the report labelled as AI-generated

Quotes the model can't back with exact text from your input are removed, and the UI says
how many were dropped. The built-in "example report" (shown only when no API key is
configured) is hand-written and clearly labelled as not AI output.

## Run locally

Requires Python 3.11+ (developed on 3.11; also installed and tested on 3.12).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then edit .env and set GEMINI_API_KEY
streamlit run app.py
```

A free key is available at https://aistudio.google.com/apikey. Without a key the app still
starts and explains that AI analysis isn't configured.

## Environment variables

Use placeholders in docs and never commit real values. `.env` is git-ignored.

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | For live analysis | Google AI Studio key. Read server-side from the environment or `.env`, or from Streamlit **Secrets** when deployed. It is never sent to the browser. |
| `SIGNALSORT_MODEL` | No | Overrides the default model (`gemini-3.8-flash`). |

On Streamlit Community Cloud, add this under **Advanced settings → Secrets**, as a
top-level line with no `[section]` header:

```toml
GEMINI_API_KEY = "your-key-here"
```

## Architecture and AI data flow

```
Browser ── pasted text ──▶ Streamlit server (app.py)
                               │  validate length (40–30,000 chars)
                               ▼
                         analyzer.analyse()
                               │  one request: system prompt + <feedback>…</feedback>
                               ▼
                    Google Gemini API (JSON-schema response)
                               │
                               ▼
              Pydantic validation (models.py, one retry on failure)
                               ▼
              quote grounding: drop any quote not found in the input
                               ▼
                    UI rendering + Markdown / CSV export
```

- **What leaves your machine:** the text you paste is sent from the Streamlit server to the
  Google Gemini API. SignalSort stores nothing: there is no database, and results exist only
  in the browser session. On the free tier Google may use submitted content to improve its
  products (also stated in the app footer), so don't paste confidential or personal data.
- **Single structured call.** The reply is constrained to a JSON schema generated from
  `models.Analysis` and validated with Pydantic.
- **Quote grounding.** Each quote is compared with the input after normalising case,
  whitespace and typographic quotes/dashes; non-matching quotes are removed.
- **No invented numbers.** Prevalence is an AI estimate, not a count.
- **Prompt-injection posture.** Feedback is wrapped in `<feedback>` tags and the prompt tells
  the model to treat it as data. This reduces risk but is not a guarantee.
- **Resilience.** Transient server errors are retried (3 attempts). On overload or quota
  errors the app tries a second free model (`gemini-3.6-flash`) once, and the report banner
  names the model that actually produced the analysis.
- **Safe rendering and export.** Model and user text is escaped before display, and CSV
  cells starting with `= + - @` are prefixed to prevent spreadsheet formula injection.

| File | Role |
|---|---|
| `app.py` | Streamlit UI and session state (entry point) |
| `analyzer.py` | Input checks, prompt, Gemini call, error mapping, fallback, quote grounding |
| `models.py` | Pydantic schema shared by the prompt and the validator |
| `report.py` | Markdown and CSV export |
| `samples.py` | Sample dataset (fictional app "Trackly") and the hand-written example report |
| `tests/` | Unit tests and headless UI tests |

## Deploy (Streamlit Community Cloud)

1. On https://share.streamlit.io choose **Create app** and pick this repository, branch
   `main`, main file path `app.py`.
2. Under **Advanced settings**, set Python 3.12 and add the `GEMINI_API_KEY` secret (above).
3. Deploy. After changing secrets, use **⋮ → Reboot app**.

The app has no login, so everyone with the URL shares one free-tier quota. The
10-analyses-per-session cap is only a soft guard (a page refresh resets it).

## Tests

```bash
pip install pytest
python -m pytest -q
```

Tests use a fake LLM client and Streamlit's headless `AppTest`, so they need no API key and
make no network calls.

**Verified results (run during development):**

- `python -m pytest -q` → **33 passed** on Python 3.11.7 (local venv).
- The same suite → **33 passed** on Python 3.12.4 in a fresh clone of this repository with
  dependencies installed only from `requirements.txt`.
- The tests cover input validation, quote grounding, schema validation and retry, error
  mapping, model fallback, CSV/Markdown export, and the main UI states.

**Not covered by automated tests:** real Gemini responses (they are non-deterministic and
rate-limited), visual layout, and mobile rendering. In manual development runs on the
sample dataset the live Gemini API returned valid structured output, and no quotes were
removed by the grounding check. That is a handful of runs on one dataset, not an evaluation.

## Known limitations

- **No accuracy evaluation.** Theme quality, sentiment labels and priorities are model
  judgement and haven't been benchmarked against human labels. Treat output as a draft.
- **Grounding checks text, not meaning.** A quote is guaranteed to exist in your input, but
  not guaranteed to be the best evidence for the theme it's attached to.
- Quote matching ignores case and whitespace, so a displayed quote can differ from the
  source in capitalisation only.
- Input is capped at 30,000 characters per analysis, with no chunking for larger datasets.
- English-language feedback only has been considered; other languages are untested.
- Free-tier Gemini has rate limits, can be overloaded, and may use submitted content for
  product improvement. The shared public quota can run out.
- No accounts, history, payments or integrations (out of scope for this MVP).

## Future improvements

- Evaluate against a labelled feedback set and tune the prompt and model choice.
- Chunk and merge very large datasets; accept CSV/file upload.
- Count mentions deterministically (e.g. per-item tagging) so frequencies can be exact.
- Paid-tier key with no training on inputs, plus real rate limiting and authentication.
- Saved analyses and trend comparison over time.
