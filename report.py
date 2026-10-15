"""Export an analysis as Markdown or CSV."""

import csv
import io

from models import Analysis


def to_markdown(analysis: Analysis, provenance: str) -> str:
    lines = [
        "# SignalSort feedback report",
        "",
        f"_{provenance}_",
        "",
        "## Summary",
        "",
        analysis.summary,
        "",
        f"**Overall sentiment:** {analysis.overall_sentiment.title()}",
        "",
        "## Themes",
        "",
    ]
    for theme in analysis.themes:
        lines += [
            f"### {theme.name}",
            "",
            f"Sentiment: {theme.sentiment.title()} · "
            f"Estimated prevalence: {theme.prevalence.title()}",
            "",
            theme.description,
            "",
        ]
        lines += [f'> "{q}"' + "\n" for q in theme.quotes] or ["_No verified evidence quotes._", ""]
    lines += ["## Recommendations", ""]
    for rec in analysis.recommendations:
        lines += [
            f"- **{rec.priority}: {rec.action}**  ",
            f"  {rec.rationale}  ",
            f"  _Themes: {', '.join(rec.related_themes)}_",
        ]
    lines += ["", "---", "Prevalence levels are AI estimates, not exact counts."]
    return "\n".join(lines) + "\n"


def to_csv(analysis: Analysis) -> str:
    """One row per theme and one per recommendation, in a single flat table."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["type", "priority", "title", "sentiment", "estimated_prevalence",
                     "detail", "evidence_or_themes"])
    for t in analysis.themes:
        writer.writerow(["theme", "", t.name, t.sentiment, t.prevalence, t.description,
                         " | ".join(t.quotes)])
    for r in analysis.recommendations:
        writer.writerow(["recommendation", r.priority, r.action, "", "", r.rationale,
                         " | ".join(r.related_themes)])
    return buf.getvalue()
