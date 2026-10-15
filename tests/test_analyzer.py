import csv
import io
import json
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from analyzer import AnalysisError, analyse, ground_quotes, is_grounded, normalise, validate_input
from models import Analysis
from report import to_csv, to_markdown
from samples import DEMO_ANALYSIS, SAMPLE_FEEDBACK

FEEDBACK = (
    "The app is “really slow” on Android.\n\nBilling charged me twice!   Please fix.\n"
    "Love the   kanban boards."
)

VALID = {
    "summary": "Mixed feedback.",
    "overall_sentiment": "mixed",
    "themes": [
        {
            "name": "Performance",
            "description": "Slow app.",
            "sentiment": "negative",
            "prevalence": "high",
            "quotes": ['The app is "really slow" on Android.', "The app crashes on login."],
        },
        {
            "name": "Boards",
            "description": "Liked.",
            "sentiment": "positive",
            "prevalence": "low",
            "quotes": ["love the kanban boards"],
        },
    ],
    "recommendations": [
        {"priority": "P1", "action": "Fix speed.", "rationale": "Top complaint.",
         "related_themes": ["Performance"]},
    ],
}


class FakeClient:
    """Stands in for genai.Client; returns queued replies or raises queued errors."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.models = self

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        finish_reason, text, block_reason = (*reply, None)[:3]
        return SimpleNamespace(
            text=text,
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=finish_reason))],
            prompt_feedback=SimpleNamespace(block_reason=block_reason),
        )


def ok(payload):
    return ("STOP", json.dumps(payload))


def api_error(code, message="error"):
    cls = errors.ClientError if code < 500 else errors.ServerError
    return cls(code, {"error": {"code": code, "message": message, "status": "X"}})


# ── Input validation ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", ["", "   \n ", None])
def test_empty_input_rejected(text):
    with pytest.raises(AnalysisError, match="Paste some"):
        validate_input(text)


def test_short_input_rejected():
    with pytest.raises(AnalysisError, match="too short"):
        validate_input("too short")


def test_long_input_rejected():
    with pytest.raises(AnalysisError, match="limit"):
        validate_input("x" * 30_001)


# ── Quote grounding ──────────────────────────────────────────────────────────

def test_normalise_handles_typography_case_and_whitespace():
    assert normalise("“Hello”   World\n—ok") == '"hello" world -ok'


def test_grounding_accepts_verbatim_and_rejects_invented():
    src = normalise(FEEDBACK)
    assert is_grounded("charged me twice", src)
    assert is_grounded('"Billing charged me twice!"', src)  # wrapping quotes ignored
    assert not is_grounded("The app crashes on login.", src)
    assert not is_grounded("app is ... slow", src)  # elisions are not verbatim
    assert not is_grounded('  ""  ', src)


def test_ground_quotes_counts_removals():
    analysis, removed = ground_quotes(Analysis.model_validate(VALID), FEEDBACK)
    assert removed == 1
    assert analysis.themes[0].quotes == ['The app is "really slow" on Android.']
    assert analysis.themes[1].quotes == ["love the kanban boards"]


def test_demo_report_quotes_are_all_verbatim_in_sample():
    _, removed = ground_quotes(DEMO_ANALYSIS.model_copy(deep=True), SAMPLE_FEEDBACK)
    assert removed == 0


# ── analyse() end to end with a fake client ──────────────────────────────────

def test_analyse_success_grounds_quotes():
    client = FakeClient(ok(VALID))
    result = analyse(FEEDBACK, client=client, model="test-model")
    config = client.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == Analysis.model_json_schema()
    assert "<feedback>" in client.calls[0]["contents"]
    assert result.removed_quotes == 1
    assert result.model == "test-model"
    assert result.analysis.recommendations[0].priority == "P1"


def test_malformed_then_valid_retries_once():
    client = FakeClient(("STOP", "not json"), ok(VALID))
    analyse(FEEDBACK, client=client)
    assert len(client.calls) == 2


def test_malformed_twice_raises():
    bad_schema = {**VALID, "overall_sentiment": "ecstatic"}
    client = FakeClient(("STOP", "{oops"), ok(bad_schema))
    with pytest.raises(AnalysisError, match="unexpected format"):
        analyse(FEEDBACK, client=client)


def test_blocks_and_truncation_are_reported():
    with pytest.raises(AnalysisError, match="declined"):
        analyse(FEEDBACK, client=FakeClient(("SAFETY", None)))
    with pytest.raises(AnalysisError, match="declined"):
        analyse(FEEDBACK, client=FakeClient(("STOP", None, "PROHIBITED_CONTENT")))
    with pytest.raises(AnalysisError, match="cut off"):
        analyse(FEEDBACK, client=FakeClient(("MAX_TOKENS", '{"summary": "trunc')))


@pytest.mark.parametrize("error, expected", [
    (api_error(429, "Resource exhausted"), "free-tier rate limit"),
    (api_error(400, "API key not valid. Please pass a valid API key."), "key was rejected"),
    (api_error(403), "key was rejected"),
    (api_error(404), "model was not found"),
    (api_error(503), "returned an error \\(503\\)"),
    (httpx.ConnectError("boom"), "Couldn't reach"),
])
def test_api_errors_become_friendly_messages(error, expected):
    with pytest.raises(AnalysisError, match=expected):
        analyse(FEEDBACK, client=FakeClient(error, error))  # second reply: fallback model


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AnalysisError, match="No API key"):
        analyse(FEEDBACK)


def test_real_sdk_config_accepts_our_schema():
    from google.genai import types
    config = types.GenerateContentConfig(response_mime_type="application/json",
                                         response_json_schema=Analysis.model_json_schema())
    assert config.response_json_schema["type"] == "object"


# ── Exports ──────────────────────────────────────────────────────────────────

def test_exports_contain_report_content():
    md = to_markdown(DEMO_ANALYSIS, "Example report")
    assert "# SignalSort feedback report" in md and "_Example report_" in md
    assert "Billing errors" in md and "P1:" in md
    rows = list(csv.reader(io.StringIO(to_csv(DEMO_ANALYSIS))))
    assert rows[0][0] == "type"
    assert len(rows) == 1 + len(DEMO_ANALYSIS.themes) + len(DEMO_ANALYSIS.recommendations)


def test_csv_neutralises_spreadsheet_formulas():
    a = DEMO_ANALYSIS.model_copy(deep=True)
    a.themes[0].quotes = ['=HYPERLINK("http://evil.example","Click")']
    a.recommendations[0].action = "+cmd|' /C calc'!A0"
    rows = list(csv.reader(io.StringIO(to_csv(a))))
    assert rows[1][6].startswith("'=HYPERLINK")
    assert rows[1 + len(a.themes)][2].startswith("'+cmd")


def test_client_is_built_with_retry_for_transient_errors_only(monkeypatch):
    captured = {}

    class Spy:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.models = FakeClient(ok(VALID))

    monkeypatch.setattr("analyzer.genai.Client", Spy)
    analyse(FEEDBACK, api_key="test-key")
    retry = captured["http_options"].retry_options
    assert retry.attempts == 3
    assert 503 in retry.http_status_codes and 429 not in retry.http_status_codes


def test_capacity_error_falls_back_to_second_model():
    client = FakeClient(api_error(503), ok(VALID))
    result = analyse(FEEDBACK, client=client, model="primary-model")
    assert [c["model"] for c in client.calls] == ["primary-model", "gemini-3.6-flash"]
    assert result.model == "gemini-3.6-flash"


def test_quota_error_falls_back_but_auth_error_does_not():
    client = FakeClient(api_error(429), ok(VALID))
    assert analyse(FEEDBACK, client=client, model="primary-model").model == "gemini-3.6-flash"
    client = FakeClient(api_error(403), ok(VALID))
    with pytest.raises(AnalysisError, match="key was rejected"):
        analyse(FEEDBACK, client=client, model="primary-model")
    assert len(client.calls) == 1


def test_both_models_overloaded_reports_first_error():
    client = FakeClient(api_error(503), api_error(429))
    with pytest.raises(AnalysisError, match="returned an error \\(503\\)"):
        analyse(FEEDBACK, client=client, model="primary-model")
