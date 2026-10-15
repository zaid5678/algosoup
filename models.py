"""Structured schema for a SignalSort analysis.

The same models define the JSON schema sent to the LLM and validate its reply.
"""

from typing import Literal

from pydantic import BaseModel, Field

Sentiment = Literal["positive", "negative", "mixed", "neutral"]
Prevalence = Literal["high", "medium", "low"]
Priority = Literal["P1", "P2", "P3"]


class Theme(BaseModel):
    name: str = Field(description="Short theme label, 2-6 words.")
    description: str = Field(description="One or two sentences explaining the theme.")
    sentiment: Sentiment
    prevalence: Prevalence = Field(
        description="Rough estimate of how often this theme appears relative to the others."
    )
    quotes: list[str] = Field(
        description=(
            "1-3 short passages copied character-for-character from the feedback. "
            "Never paraphrase, merge, or correct them."
        )
    )


class Recommendation(BaseModel):
    priority: Priority
    action: str = Field(description="A concrete, actionable step, starting with a verb.")
    rationale: str = Field(description="Why this matters, grounded in the feedback.")
    related_themes: list[str] = Field(description="Names of the themes this addresses.")


class Analysis(BaseModel):
    summary: str = Field(description="A concise 2-4 sentence overall summary.")
    overall_sentiment: Sentiment
    themes: list[Theme]
    recommendations: list[Recommendation]
