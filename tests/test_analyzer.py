import csv
import io
import json
from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest

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
    """Stands in for anthropic.Anthropic; returns queued replies or raises queued errors."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        stop_reason, text = reply
        return SimpleNamespace(stop_reason=stop_reason,
                               content=[SimpleNamespace(type="text", text=text)])


def ok(payload):
    return ("end_turn", json.dumps(payload))


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
    assert result.removed_quotes == 1
    assert result.model == "test-model"
    assert result.analysis.recommendations[0].priority == "P1"


def test_malformed_then_valid_retries_once():
    client = FakeClient(("end_turn", "not json"), ok(VALID))
    analyse(FEEDBACK, client=client)
    assert client.calls == 2


def test_malformed_twice_raises():
    bad_schema = {**VALID, "overall_sentiment": "ecstatic"}
    client = FakeClient(("end_turn", "{oops"), ok(bad_schema))
    with pytest.raises(AnalysisError, match="unexpected format"):
        analyse(FEEDBACK, client=client)


def test_refusal_and_truncation_are_reported():
    with pytest.raises(AnalysisError, match="declined"):
        analyse(FEEDBACK, client=FakeClient(("refusal", "")))
    with pytest.raises(AnalysisError, match="cut off"):
        analyse(FEEDBACK, client=FakeClient(("max_tokens", '{"summary": "trunc')))


def test_api_errors_become_friendly_messages():
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    with pytest.raises(AnalysisError, match="Couldn't reach"):
        analyse(FEEDBACK, client=FakeClient(anthropic.APIConnectionError(request=req)))
    resp = httpx.Response(429, request=req)
    rate_limited = anthropic.RateLimitError("rate limited", response=resp, body=None)
    with pytest.raises(AnalysisError, match="Rate limit"):
        analyse(FEEDBACK, client=FakeClient(rate_limited))


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AnalysisError, match="No API key"):
        analyse(FEEDBACK)


def test_schema_is_accepted_by_sdk_transform():
    schema = anthropic.transform_schema(Analysis)
    assert schema["type"] == "object"


# ── Exports ──────────────────────────────────────────────────────────────────

def test_exports_contain_report_content():
    md = to_markdown(DEMO_ANALYSIS, "Example report")
    assert "# SignalSort feedback report" in md and "_Example report_" in md
    assert "Billing errors" in md and "P1:" in md
    rows = list(csv.reader(io.StringIO(to_csv(DEMO_ANALYSIS))))
    assert rows[0][0] == "type"
    assert len(rows) == 1 + len(DEMO_ANALYSIS.themes) + len(DEMO_ANALYSIS.recommendations)
