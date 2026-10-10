"""D3 fresh-stream replication, frozen in CRITICAL-PATH section 9. Local only."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.screening_survey import main

NAME = 'd3-screening-replication-v1'
PROFILES = ((17, 3, 16, 12),)
LABELS = tuple(range(2026101001, 2026101025))
REPETITIONS = 3
DEADLINE_SECONDS = 240


if __name__ == '__main__':
    main(name=NAME, profiles=PROFILES, labels=LABELS, repetitions=REPETITIONS,
         deadline_seconds=DEADLINE_SECONDS, primary_profiles=PROFILES)
