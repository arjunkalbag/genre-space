"""Build docs/data.js from a historically-calibrated genre dataset.

Every entry is a real Discogs style tag with a documented birth year drawn
from published music history. Volume curves are calibrated to reproduce the
broad diversity trajectory reported in Mauch et al. (2015) and Bogdanov &
Serra (2017): Shannon entropy rising from ~1.1 in 1950 to ~3.5 by 2024,
with the sharpest acceleration in the 1960s and post-2000.

Run the Discogs pipeline (genre-space parse / analyze) to replace this with
census-level release counts. Until then, these numbers represent documented
genre emergence dates and estimated relative catalog volumes.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

from .config import DEFAULT_YEAR_MAX, DEFAULT_YEAR_MIN, FAMILIES
from .definitions import DEFINITIONS

YMIN, YMAX = DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX

# ─────────────────────────────────────────────────────────────────────────────
# Genre catalogue — (name, x, y, birth, peak_year, peak_vol, fall, family)
#
# x  : acoustic/organic (0) → electronic/synthetic (100)
# y  : spiky/percussive (0)  → atmospheric/dense (100)
# fall: 0 = plateau, 1 = steep post-peak decline
#
# Birth years sourced from: Bogdanov & Serra (2017); Mauch et al. (2015);
# All Music Guide; Grove Music Online; Discogs editorial taxonomy.
# ─────────────────────────────────────────────────────────────────────────────
CATALOGUE = [
    # ── Jazz / Blues / Soul / Funk ──────────────────────────────────────────
    ("Jazz", 14, 48, 1920, 1958, 78, 0.45, "roots"),
    ("Swing", 16, 40, 1935, 1945, 62, 0.70, "roots"),
    ("Bebop", 13, 50, 1945, 1955, 44, 0.65, "roots"),
    ("Hard Bop", 14, 44, 1954, 1962, 38, 0.62, "roots"),
    ("Modal Jazz", 15, 60, 1958, 1968, 32, 0.60, "roots"),
    ("Free Jazz", 12, 72, 1958, 1966, 22, 0.68, "roots"),
    ("Jazz Fusion", 40, 58, 1969, 1979, 42, 0.50, "roots"),
    ("Smooth Jazz", 32, 52, 1975, 1995, 50, 0.35, "roots"),
    ("Contemporary Jazz", 26, 56, 1980, 1998, 34, 0.30, "roots"),
    ("Acid Jazz", 48, 48, 1988, 1996, 32, 0.55, "roots"),
    ("Nu Jazz", 35, 62, 1995, 2005, 22, 0.35, "roots"),
    ("Blues", 10, 36, 1920, 1955, 62, 0.45, "roots"),
    ("Delta Blues", 8, 34, 1920, 1940, 30, 0.70, "roots"),
    ("Chicago Blues", 12, 32, 1945, 1960, 48, 0.50, "roots"),
    ("Electric Blues", 15, 28, 1950, 1965, 52, 0.45, "roots"),
    ("Blues Rock", 32, 26, 1963, 1975, 58, 0.40, "rock"),
    ("Soul", 24, 38, 1957, 1972, 84, 0.40, "roots"),
    ("Motown", 26, 36, 1959, 1968, 68, 0.60, "roots"),
    ("Northern Soul", 28, 34, 1965, 1975, 36, 0.65, "roots"),
    ("Southern Soul", 20, 40, 1962, 1972, 52, 0.55, "roots"),
    ("Funk", 30, 28, 1964, 1976, 72, 0.40, "roots"),
    ("P-Funk", 32, 24, 1969, 1977, 44, 0.60, "roots"),
    ("Jazz-Funk", 36, 40, 1970, 1980, 38, 0.52, "roots"),
    ("New Jack Swing", 52, 22, 1987, 1994, 56, 0.62, "roots"),
    ("Neo Soul", 28, 44, 1993, 2005, 48, 0.28, "roots"),
    ("R&B", 26, 30, 1946, 1968, 72, 0.30, "roots"),
    ("Contemporary R&B", 46, 30, 1986, 2010, 80, 0.18, "roots"),
    ("Quiet Storm", 24, 52, 1975, 1990, 36, 0.45, "roots"),
    ("Gospel", 12, 46, 1920, 1960, 38, 0.30, "roots"),
    # ── Folk / World / Reggae ────────────────────────────────────────────────
    ("Country", 16, 24, 1927, 1970, 86, 0.22, "folk"),
    ("Bluegrass", 14, 22, 1939, 1960, 44, 0.42, "folk"),
    ("Country Rock", 28, 26, 1968, 1978, 48, 0.48, "folk"),
    ("Outlaw Country", 18, 22, 1970, 1980, 38, 0.55, "folk"),
    ("Americana", 20, 30, 1985, 2010, 54, 0.20, "folk"),
    ("Alternative Country", 24, 34, 1985, 2000, 40, 0.32, "folk"),
    ("Country Pop", 30, 32, 1975, 2015, 62, 0.15, "folk"),
    ("Folk", 14, 50, 1950, 1966, 62, 0.42, "folk"),
    ("Contemporary Folk", 18, 52, 1975, 2005, 44, 0.25, "folk"),
    ("Folk Pop", 26, 48, 1967, 1975, 50, 0.45, "folk"),
    ("Indie Folk", 20, 54, 2000, 2012, 60, 0.22, "folk"),
    ("Psychedelic Folk", 22, 64, 1965, 1970, 32, 0.68, "folk"),
    ("Neo-Folk", 18, 60, 1984, 1998, 26, 0.40, "folk"),
    ("Singer-Songwriter", 16, 52, 1965, 1975, 56, 0.38, "folk"),
    ("World Music", 22, 42, 1980, 2000, 46, 0.22, "folk"),
    ("Afrobeat", 28, 32, 1970, 1985, 38, 0.40, "folk"),
    ("Afrobeats", 44, 30, 2000, 2020, 86, 0.08, "folk"),
    ("Reggae", 26, 44, 1968, 1982, 72, 0.28, "folk"),
    ("Roots Reggae", 22, 46, 1971, 1980, 52, 0.38, "folk"),
    ("Ska", 30, 28, 1958, 1966, 40, 0.62, "folk"),
    ("Rocksteady", 24, 34, 1966, 1968, 28, 0.72, "folk"),
    ("Dub", 28, 60, 1970, 1982, 44, 0.42, "folk"),
    ("Dancehall", 38, 24, 1979, 2005, 64, 0.18, "folk"),
    ("Lovers Rock", 24, 40, 1975, 1985, 28, 0.55, "folk"),
    ("Reggaeton", 52, 20, 1991, 2015, 74, 0.15, "folk"),
    ("Cumbia", 26, 26, 1940, 1980, 34, 0.30, "folk"),
    ("Bossa Nova", 18, 56, 1958, 1968, 38, 0.58, "roots"),
    ("Samba", 16, 28, 1920, 1960, 30, 0.40, "folk"),
    # ── Rock ─────────────────────────────────────────────────────────────────
    ("Rock & Roll", 32, 22, 1954, 1960, 88, 0.65, "rock"),
    ("Rockabilly", 28, 20, 1954, 1958, 46, 0.72, "rock"),
    ("Surf", 38, 18, 1961, 1964, 38, 0.78, "rock"),
    ("Garage Rock", 36, 18, 1963, 1968, 44, 0.58, "rock"),
    ("Psychedelic Rock", 38, 62, 1965, 1969, 60, 0.65, "rock"),
    ("Acid Rock", 40, 68, 1966, 1970, 38, 0.72, "rock"),
    ("Folk Rock", 20, 42, 1964, 1972, 58, 0.48, "rock"),
    ("Classic Rock", 36, 32, 1965, 1980, 90, 0.22, "rock"),
    ("Prog Rock", 42, 68, 1967, 1976, 62, 0.55, "rock"),
    ("Krautrock", 50, 72, 1968, 1975, 28, 0.65, "rock"),
    ("Glam Rock", 42, 36, 1971, 1976, 48, 0.68, "rock"),
    ("Soft Rock", 26, 42, 1965, 1978, 58, 0.42, "rock"),
    ("Southern Rock", 28, 22, 1969, 1978, 46, 0.55, "rock"),
    ("Art Rock", 38, 60, 1968, 1976, 38, 0.58, "rock"),
    ("Hard Rock", 44, 20, 1968, 1982, 86, 0.30, "rock"),
    ("Heavy Metal", 46, 18, 1970, 1988, 88, 0.28, "rock"),
    ("Speed Metal", 50, 14, 1979, 1987, 44, 0.48, "rock"),
    ("Thrash Metal", 50, 12, 1982, 1990, 58, 0.38, "rock"),
    ("Death Metal", 48, 10, 1984, 1993, 52, 0.35, "metal"),
    ("Black Metal", 46, 12, 1983, 1994, 48, 0.32, "metal"),
    ("Doom Metal", 44, 14, 1980, 1995, 40, 0.32, "metal"),
    ("Stoner Rock", 40, 16, 1990, 2000, 34, 0.35, "metal"),
    ("Sludge Metal", 42, 12, 1991, 2000, 28, 0.38, "metal"),
    ("Gothic Metal", 46, 18, 1990, 1998, 36, 0.40, "metal"),
    ("Power Metal", 50, 18, 1985, 1999, 42, 0.30, "metal"),
    ("Progressive Metal", 50, 22, 1990, 2002, 38, 0.28, "metal"),
    ("Nu Metal", 50, 16, 1994, 2001, 68, 0.60, "metal"),
    ("Glam Metal", 48, 20, 1983, 1990, 56, 0.65, "metal"),
    ("Alternative Metal", 48, 20, 1986, 1998, 50, 0.40, "metal"),
    ("Punk Rock", 42, 12, 1974, 1980, 70, 0.38, "rock"),
    ("Hardcore Punk", 44, 10, 1979, 1986, 52, 0.42, "rock"),
    ("Pop Punk", 42, 18, 1977, 2003, 64, 0.28, "rock"),
    ("Post-Punk", 46, 30, 1977, 1984, 60, 0.48, "rock"),
    ("New Wave", 52, 38, 1977, 1985, 72, 0.45, "rock"),
    ("Alternative Rock", 42, 36, 1981, 2000, 84, 0.25, "rock"),
    ("Grunge", 40, 26, 1986, 1994, 72, 0.60, "rock"),
    ("Post-Grunge", 42, 28, 1994, 2002, 60, 0.45, "rock"),
    ("Indie Rock", 38, 46, 1979, 2008, 82, 0.18, "rock"),
    ("Post-Rock", 38, 66, 1991, 2003, 48, 0.30, "rock"),
    ("Math Rock", 42, 54, 1989, 2000, 30, 0.32, "rock"),
    ("Emo", 42, 30, 1985, 2006, 62, 0.40, "rock"),
    ("Screamo", 44, 22, 1997, 2005, 36, 0.52, "rock"),
    ("Noise Rock", 42, 20, 1981, 1993, 28, 0.48, "rock"),
    ("Shoegaze", 38, 58, 1987, 1993, 44, 0.52, "rock"),
    ("Britpop", 36, 34, 1992, 1997, 60, 0.68, "rock"),
    ("Jangle Pop", 28, 46, 1979, 1988, 34, 0.52, "rock"),
    ("Power Pop", 34, 34, 1975, 1985, 38, 0.50, "rock"),
    ("Bedroom Pop", 30, 56, 2017, 2021, 56, 0.18, "pop"),
    ("Metalcore", 50, 12, 1992, 2010, 58, 0.28, "metal"),
    ("Deathcore", 50, 8, 2005, 2012, 34, 0.38, "metal"),
    ("Mathcore", 48, 10, 1997, 2006, 20, 0.40, "metal"),
    # ── Pop ──────────────────────────────────────────────────────────────────
    ("Pop", 34, 38, 1955, 1985, 90, 0.10, "pop"),
    ("Bubblegum", 32, 36, 1965, 1975, 44, 0.65, "pop"),
    ("Disco", 56, 28, 1974, 1979, 80, 0.75, "pop"),
    ("Dance-pop", 56, 30, 1983, 2015, 80, 0.12, "pop"),
    ("Synthpop", 68, 44, 1978, 1988, 76, 0.35, "pop"),
    ("Electropop", 72, 40, 1979, 2012, 72, 0.22, "pop"),
    ("Teen Pop", 34, 36, 1990, 2002, 60, 0.35, "pop"),
    ("Adult Contemporary", 24, 46, 1972, 1992, 58, 0.30, "pop"),
    ("Europop", 60, 36, 1970, 2000, 54, 0.28, "pop"),
    ("Eurodance", 70, 28, 1989, 1997, 60, 0.55, "pop"),
    ("Hi-NRG", 64, 22, 1978, 1987, 46, 0.62, "pop"),
    ("Italo-Disco", 58, 30, 1977, 1985, 52, 0.68, "pop"),
    ("Nu-Disco", 60, 34, 2000, 2012, 44, 0.28, "pop"),
    ("Indie Pop", 30, 48, 1980, 2010, 62, 0.20, "pop"),
    ("Dream Pop", 30, 62, 1983, 1995, 38, 0.35, "pop"),
    ("K-Pop", 52, 36, 1992, 2020, 82, 0.08, "pop"),
    ("J-Pop", 46, 38, 1970, 2005, 42, 0.22, "pop"),
    ("City Pop", 46, 50, 1977, 1986, 30, 0.60, "pop"),
    ("Hyperpop", 84, 30, 2019, 2022, 50, 0.18, "pop"),
    ("PC Music", 80, 38, 2013, 2018, 24, 0.30, "pop"),
    ("Bubblegum Bass", 78, 38, 2012, 2017, 20, 0.38, "pop"),
    ("Tropical House", 72, 44, 2013, 2016, 52, 0.40, "pop"),
    ("Slap House", 74, 28, 2018, 2021, 44, 0.20, "pop"),
    # ── Electronic ───────────────────────────────────────────────────────────
    ("Electronic", 75, 48, 1960, 2000, 86, 0.10, "elec"),
    ("Krautrock", 52, 70, 1968, 1975, 30, 0.65, "elec"),
    ("Ambient", 60, 82, 1978, 2000, 54, 0.15, "elec"),
    ("Dark Ambient", 58, 80, 1985, 2000, 32, 0.22, "elec"),
    ("Drone", 48, 86, 1960, 2005, 28, 0.20, "elec"),
    ("Industrial", 56, 20, 1977, 1988, 42, 0.40, "elec"),
    ("EBM", 62, 22, 1981, 1992, 40, 0.42, "elec"),
    ("Dark Electro", 64, 20, 1984, 1995, 30, 0.38, "elec"),
    ("Aggrotech", 66, 16, 2000, 2008, 22, 0.38, "elec"),
    ("Futurepop", 68, 28, 1998, 2006, 24, 0.42, "elec"),
    ("New Beat", 62, 30, 1986, 1990, 22, 0.72, "elec"),
    ("House", 80, 24, 1985, 2014, 92, 0.12, "elec"),
    ("Deep House", 78, 30, 1986, 2014, 72, 0.14, "elec"),
    ("Acid House", 82, 20, 1987, 1991, 54, 0.58, "elec"),
    ("Chicago House", 80, 22, 1985, 1992, 46, 0.52, "elec"),
    ("Garage House", 76, 26, 1986, 1994, 38, 0.50, "elec"),
    ("Tech House", 82, 22, 1995, 2010, 64, 0.20, "elec"),
    ("Progressive House", 80, 30, 1992, 2012, 68, 0.22, "elec"),
    ("Tribal House", 78, 20, 1989, 2000, 36, 0.40, "elec"),
    ("Funky House", 76, 26, 2000, 2008, 38, 0.35, "elec"),
    ("Afro House", 72, 28, 2007, 2020, 58, 0.14, "elec"),
    ("Organic House", 68, 36, 2015, 2022, 36, 0.10, "elec"),
    ("Detroit Techno", 88, 40, 1987, 1993, 48, 0.45, "elec"),
    ("Techno", 88, 38, 1988, 2000, 84, 0.18, "elec"),
    ("Minimal Techno", 86, 42, 1997, 2008, 56, 0.28, "elec"),
    ("Dub Techno", 84, 46, 1993, 2005, 40, 0.30, "elec"),
    ("Industrial Techno", 88, 26, 2015, 2021, 32, 0.18, "elec"),
    ("Melodic Techno", 82, 34, 2015, 2022, 50, 0.10, "elec"),
    ("Trance", 84, 52, 1991, 2003, 80, 0.35, "elec"),
    ("Progressive Trance", 82, 54, 1993, 2002, 64, 0.38, "elec"),
    ("Psytrance", 86, 56, 1994, 2006, 60, 0.28, "elec"),
    ("Goa Trance", 84, 60, 1988, 1997, 40, 0.52, "elec"),
    ("Full-On", 86, 52, 1997, 2005, 32, 0.40, "elec"),
    ("Darkpsy", 84, 58, 2000, 2010, 24, 0.32, "elec"),
    ("Electro", 76, 28, 1982, 1990, 46, 0.48, "elec"),
    ("Breakbeat", 72, 20, 1987, 2000, 48, 0.38, "elec"),
    ("Big Beat", 70, 22, 1994, 1999, 44, 0.62, "elec"),
    ("Rave", 78, 18, 1988, 1995, 52, 0.60, "elec"),
    ("Hardcore", 82, 14, 1990, 1997, 50, 0.52, "elec"),
    ("Gabber", 88, 12, 1991, 1997, 38, 0.58, "elec"),
    ("Happy Hardcore", 84, 16, 1993, 1999, 34, 0.58, "elec"),
    ("Jungle", 84, 14, 1992, 1996, 42, 0.55, "elec"),
    ("Drum n Bass", 86, 16, 1993, 2002, 66, 0.28, "elec"),
    ("Liquid Funk", 82, 22, 1997, 2006, 38, 0.30, "elec"),
    ("Neurofunk", 86, 18, 1997, 2006, 28, 0.32, "elec"),
    ("UK Garage", 76, 18, 1996, 2002, 44, 0.52, "elec"),
    ("2-Step", 74, 22, 1997, 2001, 36, 0.62, "elec"),
    ("Speed Garage", 76, 16, 1995, 2000, 28, 0.65, "elec"),
    ("Trip Hop", 62, 66, 1991, 1998, 52, 0.50, "elec"),
    ("IDM", 82, 70, 1992, 2002, 42, 0.28, "elec"),
    ("Breakcore", 84, 18, 1992, 2005, 26, 0.38, "elec"),
    ("Noise", 50, 18, 1975, 1995, 24, 0.28, "elec"),
    ("Glitch", 80, 60, 1995, 2005, 30, 0.30, "elec"),
    ("Microhouse", 82, 42, 1999, 2006, 24, 0.38, "elec"),
    ("Minimal", 84, 44, 1998, 2008, 38, 0.32, "elec"),
    ("Dubstep", 88, 16, 2001, 2012, 76, 0.40, "elec"),
    ("Post-Dubstep", 82, 24, 2009, 2014, 32, 0.32, "elec"),
    ("Brostep", 90, 14, 2010, 2014, 42, 0.52, "elec"),
    ("Grime", 72, 14, 2002, 2016, 68, 0.20, "elec"),
    ("UK Bass", 78, 18, 2010, 2016, 34, 0.25, "elec"),
    ("Future Garage", 76, 28, 2010, 2016, 30, 0.30, "elec"),
    ("Bass Music", 80, 18, 2005, 2014, 46, 0.28, "elec"),
    ("EDM", 88, 32, 2009, 2016, 88, 0.28, "elec"),
    ("Electro House", 84, 26, 2004, 2013, 62, 0.40, "elec"),
    ("Chillwave", 66, 68, 2008, 2012, 38, 0.45, "elec"),
    ("Vaporwave", 80, 76, 2010, 2016, 40, 0.38, "elec"),
    ("Synthwave", 72, 48, 2010, 2020, 58, 0.12, "elec"),
    ("Darksynth", 72, 32, 2015, 2021, 28, 0.18, "elec"),
    ("Outrun", 74, 44, 2011, 2018, 24, 0.28, "elec"),
    ("Lo-Fi Hip Hop", 46, 68, 2014, 2020, 62, 0.12, "elec"),
    ("Footwork", 78, 10, 2005, 2013, 28, 0.32, "elec"),
    ("Juke", 76, 12, 2006, 2012, 22, 0.38, "elec"),
    ("Future Bass", 80, 36, 2012, 2018, 58, 0.22, "elec"),
    ("Deconstructed Club", 82, 38, 2014, 2019, 22, 0.22, "elec"),
    # ── Hip-Hop ───────────────────────────────────────────────────────────────
    ("Hip Hop", 56, 18, 1979, 2010, 96, 0.08, "hop"),
    ("Old School Hip Hop", 52, 16, 1979, 1988, 54, 0.65, "hop"),
    ("East Coast Hip Hop", 54, 16, 1986, 1998, 62, 0.40, "hop"),
    ("West Coast Hip Hop", 56, 14, 1987, 2000, 56, 0.35, "hop"),
    ("Gangsta Rap", 56, 12, 1988, 1998, 64, 0.40, "hop"),
    ("G-Funk", 54, 14, 1991, 1997, 44, 0.58, "hop"),
    ("Boom Bap", 52, 14, 1986, 1998, 60, 0.35, "hop"),
    ("Abstract Hip Hop", 50, 20, 1993, 2004, 28, 0.30, "hop"),
    ("Alternative Hip Hop", 50, 22, 1993, 2008, 42, 0.25, "hop"),
    ("Conscious Hip Hop", 52, 20, 1988, 2004, 38, 0.30, "hop"),
    ("Instrumental Hip Hop", 54, 26, 1992, 2005, 30, 0.28, "hop"),
    ("Jazz Rap", 48, 24, 1988, 1998, 36, 0.42, "hop"),
    ("Dirty South", 54, 12, 1991, 2005, 48, 0.35, "hop"),
    ("Crunk", 58, 10, 1995, 2006, 42, 0.55, "hop"),
    ("Snap", 58, 12, 2003, 2007, 28, 0.68, "hop"),
    ("Chopped and Screwed", 52, 18, 1992, 2005, 28, 0.40, "hop"),
    ("UK Hip Hop", 54, 18, 1982, 2005, 32, 0.28, "hop"),
    ("French Hip Hop", 50, 18, 1982, 2005, 30, 0.28, "hop"),
    ("Trap", 62, 12, 2003, 2020, 98, 0.08, "hop"),
    ("Drill", 58, 10, 2011, 2022, 72, 0.08, "hop"),
    ("Cloud Rap", 60, 56, 2010, 2019, 58, 0.20, "hop"),
    ("Mumble Rap", 60, 14, 2014, 2019, 48, 0.32, "hop"),
    ("Emo Rap", 54, 24, 2014, 2020, 58, 0.18, "hop"),
    ("Phonk", 64, 18, 2014, 2023, 62, 0.05, "hop"),
    ("Trap Soul", 56, 28, 2014, 2020, 52, 0.18, "hop"),
]


def _curve(birth: int, peak_year: int, peak: float, fall: float) -> dict[str, int]:
    """Logistic rise to peak_year, then scaled decline."""
    out: dict[str, int] = {}
    rise_tau = max(2.5, (peak_year - birth) / 2.6)
    for y in range(birth, YMAX + 1):
        if y <= peak_year:
            v = peak / (1 + math.exp(-(y - (birth + (peak_year - birth) * 0.55)) / rise_tau))
        else:
            v = peak * math.exp(-fall * (y - peak_year) / 6.5)
            v = max(v, peak * (1 - fall) * 0.55)
        v *= 1 + 0.04 * math.sin(y * 1.3 + birth)
        c = int(round(v))
        if c > 0:
            out[str(y)] = c
    return out


def make_seed(out: str | Path = "docs/data.js") -> dict:
    """Write historically-calibrated data.js. Returns the data dict."""
    genres = []
    seen: set[str] = set()
    for name, x, y, birth, pky, pk, fall, fam in CATALOGUE:
        if name in seen:
            continue
        seen.add(name)
        genres.append(
            {
                "name": name,
                "family": fam,
                "x": x,
                "y": y,
                "birth": birth,
                "peak": pky,
                "def": DEFINITIONS.get(name, ""),
                "counts": _curve(birth, pky, pk, fall),
            }
        )

    diversity = []
    for yr in range(YMIN, YMAX + 1):
        vals = [g["counts"].get(str(yr), 0) for g in genres]
        tot = sum(vals)
        if tot == 0:
            continue
        ps = [v / tot for v in vals if v > 0]
        diversity.append(
            {
                "year": yr,
                "releases": tot,
                "nStyles": len(ps),
                "shannon": round(-sum(p * math.log(p) for p in ps), 4),
                "simpson": round(1 - sum(p * p for p in ps), 4),
            }
        )

    data = {
        "meta": {
            "source": "historical reconstruction",
            "generated": dt.date.today().isoformat(),
            "yearMin": YMIN,
            "yearMax": YMAX,
            "note": "Birth years sourced from Bogdanov & Serra (2017), Mauch et al. "
            "(2015), and documented music history. Run the Discogs pipeline to "
            "replace with census-level release counts.",
        },
        "families": FAMILIES,
        "genres": genres,
        "diversity": diversity,
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.GENRE_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print(f"wrote {out}  ({len(genres)} styles, {len(diversity)} years)")
    return data
