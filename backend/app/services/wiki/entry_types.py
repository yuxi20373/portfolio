"""Section templates used to keep generated wiki entries structurally
consistent within each topic category - similar to how Wikipedia articles
about similar subjects tend to share a section layout (Definition / History
/ Uses / ... for an academic term; Overview / Behavior / Habitat / Care /
Varieties for an animal, etc).

This is intentionally a small, curated set. The summarizer picks the
closest-matching type for each entry and only keeps the sections that are
actually applicable to that specific topic - it does not have to use every
heading in the list, and it may not invent headings outside this list.
"""

ENTRY_TYPE_TEMPLATES = {
    "concept": {
        "description": "Abstract or academic ideas, fields of study, theories, technical terms (e.g. 'Natural Language Processing', 'Inflation').",
        "sections": ["Definition", "History", "Uses", "Tasks and Limitations", "Practical Issues", "Trends"],
    },
    "technology": {
        "description": "Tools, software, products, techniques, protocols (e.g. 'Docker', 'HTTP').",
        "sections": ["Overview", "How It Works", "History", "Use Cases", "Limitations", "Related Technologies"],
    },
    "organism": {
        "description": "Animals, plants, or other living things (e.g. 'Betta fish', 'Monstera deliciosa').",
        "sections": ["Overview", "Behavior and Ecology", "Habitat", "Care and Keeping", "Varieties and Classification"],
    },
    "person": {
        "description": "A specific real or notable individual.",
        "sections": ["Overview", "Biography", "Major Works or Contributions", "Legacy"],
    },
    "event": {
        "description": "A specific historical or notable event.",
        "sections": ["Overview", "Background", "Timeline", "Impact"],
    },
    "place": {
        "description": "A specific location, city, region, or landmark.",
        "sections": ["Overview", "Geography", "History", "Culture and Attractions"],
    },
    "general": {
        "description": "Anything that doesn't clearly fit the other categories - the catch-all fallback.",
        "sections": ["Overview", "Key Points", "Related Information"],
    },
}
