"""Shared configuration: the colour-family taxonomy and pipeline defaults.

Centralised so the analyzer and the seed generator can't drift apart.
"""

from __future__ import annotations

# The eight colour families the visual renders. Keys are stable identifiers;
# `label` is what shows in the legend, `color` is the bubble/stream fill.
FAMILIES: dict[str, dict[str, str]] = {
    "roots": {"color": "#F2B33D", "label": "Jazz · Blues · Soul"},
    "folk": {"color": "#7BC47F", "label": "Folk · World · Reggae"},
    "rock": {"color": "#FF6F61", "label": "Rock"},
    "pop": {"color": "#F062A6", "label": "Pop"},
    "elec": {"color": "#45C4E0", "label": "Electronic"},
    "hop": {"color": "#9B7BE8", "label": "Hip-Hop"},
    "metal": {"color": "#7E8AA6", "label": "Metal"},
    "other": {"color": "#C2B8A3", "label": "Other"},
}

# Discogs top-level genres -> colour family. Anything unmapped falls back to "other".
FAMILY_OF: dict[str, str] = {
    "Blues": "roots",
    "Funk / Soul": "roots",
    "Jazz": "roots",
    "Folk, World, & Country": "folk",
    "Latin": "folk",
    "Reggae": "folk",
    "Rock": "rock",
    "Pop": "pop",
    "Electronic": "elec",
    "Hip Hop": "hop",
    "Stage & Screen": "other",
    "Classical": "other",
    "Children's": "other",
    "Brass & Military": "other",
    "Non-Music": "other",
}

DEFAULT_YEAR_MIN = 1950
DEFAULT_YEAR_MAX = 2024
DEFAULT_TOP_STYLES = 90
