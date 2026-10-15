"""Sample dataset and a pre-written example report for demo purposes.

"Trackly" is a fictional project-management app. The example report is
hand-written (not AI output) and every quote in it appears verbatim in
SAMPLE_FEEDBACK; tests/test_analyzer.py enforces that.
"""

from models import Analysis

SAMPLE_FEEDBACK = """\
[App Store review, 2 stars] Love the idea but the mobile app is painfully slow. Takes 6-7 seconds to open a project board on my iPhone.

[Support ticket #4821] We were charged twice for our annual plan this month. Please refund the duplicate payment as soon as possible.

[G2 review, 5 stars] The kanban boards are genuinely the best I've used. Drag and drop just feels right and my whole team picked it up in a day.

[Customer interview - ops manager, 40-person agency] Honestly the reporting is where it falls down. I export everything to Excel every Friday because the built-in reports can't filter by client.

[App Store review, 1 star] App crashes every time I try to attach a photo to a task. Reinstalled twice, still broken.

[Support ticket #4877] How do I set up recurring tasks? I couldn't find it anywhere in the settings.

[G2 review, 4 stars] Great for small teams. Onboarding was smooth and the templates saved us hours. Wish the reporting was more flexible though.

[Support ticket #4902] Our invoice shows the old price even though we downgraded to the Starter plan last month.

[Customer interview - product lead, SaaS startup] The Slack integration is the reason we chose Trackly. Notifications land exactly where my team already works.

[Play Store review, 2 stars] Mobile app is so slow it's basically unusable on the train. Desktop is fine.

[Support ticket #4935] Is there a way to make recurring tasks? We have weekly standups that I recreate manually.

[Customer interview - founder, design studio] Reports are too basic. I need to see hours per client per month without building a spreadsheet.

[G2 review, 5 stars] Customer support replied within 10 minutes and actually fixed my issue. Rare these days.

[Support ticket #4951] I was billed after cancelling my trial. I cancelled on the 3rd and still got charged on the 5th.

[App Store review, 3 stars] Nice design, but the app takes forever to sync between my phone and laptop.
"""

DEMO_ANALYSIS = Analysis.model_validate({
    "summary": (
        "Customers like Trackly's core boards, onboarding and Slack integration, but three "
        "problems recur: a slow, crash-prone mobile app; billing errors that charge customers "
        "incorrectly; and reporting too limited for client-based work. Several users also "
        "can't find recurring tasks."
    ),
    "overall_sentiment": "mixed",
    "themes": [
        {
            "name": "Mobile app performance",
            "description": "The mobile app is slow to open and sync, and crashes when attaching photos.",
            "sentiment": "negative",
            "prevalence": "high",
            "quotes": [
                "the mobile app is painfully slow",
                "App crashes every time I try to attach a photo to a task.",
                "the app takes forever to sync between my phone and laptop",
            ],
        },
        {
            "name": "Billing errors",
            "description": "Duplicate charges, charges after cancellation, and outdated prices on invoices.",
            "sentiment": "negative",
            "prevalence": "medium",
            "quotes": [
                "We were charged twice for our annual plan this month.",
                "I cancelled on the 3rd and still got charged on the 5th.",
            ],
        },
        {
            "name": "Limited reporting",
            "description": "Built-in reports can't filter by client or show hours per client, forcing spreadsheet exports.",
            "sentiment": "negative",
            "prevalence": "medium",
            "quotes": [
                "the built-in reports can't filter by client",
                "I need to see hours per client per month without building a spreadsheet.",
            ],
        },
        {
            "name": "Core boards and onboarding",
            "description": "Kanban boards, templates and onboarding are praised as intuitive and fast to adopt.",
            "sentiment": "positive",
            "prevalence": "medium",
            "quotes": [
                "The kanban boards are genuinely the best I've used.",
                "Onboarding was smooth and the templates saved us hours.",
            ],
        },
        {
            "name": "Recurring tasks discoverability",
            "description": "Users can't find how to create recurring tasks and recreate them by hand.",
            "sentiment": "negative",
            "prevalence": "low",
            "quotes": ["How do I set up recurring tasks?"],
        },
        {
            "name": "Integrations and support",
            "description": "The Slack integration and fast customer support are cited as reasons to choose and stay.",
            "sentiment": "positive",
            "prevalence": "low",
            "quotes": [
                "The Slack integration is the reason we chose Trackly.",
                "Customer support replied within 10 minutes and actually fixed my issue.",
            ],
        },
    ],
    "recommendations": [
        {
            "priority": "P1",
            "action": "Audit the billing system for duplicate, post-cancellation and stale-price charges, and proactively refund affected customers.",
            "rationale": "Billing errors directly cost customers money and erode trust faster than any feature gap.",
            "related_themes": ["Billing errors"],
        },
        {
            "priority": "P1",
            "action": "Profile mobile cold-start and sync times and fix the photo-attachment crash.",
            "rationale": "Mobile slowness is the most frequent complaint and is driving 1-2 star store reviews.",
            "related_themes": ["Mobile app performance"],
        },
        {
            "priority": "P2",
            "action": "Add client filters and an hours-per-client report to the built-in reporting.",
            "rationale": "Agency and studio customers are working around reporting with weekly spreadsheet exports.",
            "related_themes": ["Limited reporting"],
        },
        {
            "priority": "P3",
            "action": "Surface recurring tasks in the task creation flow and add a help-centre article.",
            "rationale": "The feature request suggests a discoverability gap, which is cheap to close.",
            "related_themes": ["Recurring tasks discoverability"],
        },
    ],
})
