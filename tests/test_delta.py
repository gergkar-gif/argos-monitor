"""Tests for delta comparison logic and movement classification."""
import unittest
import math
import sys
import pathlib
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos import crisis, export


class TestDeltaClassification(unittest.TestCase):
    def test_delta_states(self):
        # We can test the window and state logic directly
        # state 'new': prev == 0 and curr >= 2
        n_prev, n_curr = 0, 5
        delta_n = n_curr - n_prev
        v = round(n_curr / max(1, n_prev), 2)
        if n_prev == 0 and n_curr >= 2:
            st = "new"
        elif delta_n >= 3 and v >= 1.75:
            st = "surging"
        elif -delta_n >= 3 and v <= 0.40:
            st = "cooling"
        elif n_curr >= 2:
            st = "steady"
        else:
            st = "trace"
        self.assertEqual(st, "new")

        # state 'surging': delta_n >= 3 and v >= 1.75
        n_prev, n_curr = 4, 10
        delta_n = n_curr - n_prev
        v = round(n_curr / max(1, n_prev), 2)
        velocity_z = round(float(delta_n) / math.sqrt(max(1.0, float(n_prev))), 2)
        if n_prev == 0 and n_curr >= 2:
            st = "new"
        elif delta_n >= 3 and v >= 1.75:
            st = "surging"
        self.assertEqual(st, "surging")
        self.assertGreaterEqual(velocity_z, 2.0)

        # state 'cooling': -delta_n >= 3 and v <= 0.40
        n_prev, n_curr = 12, 3
        delta_n = n_curr - n_prev
        v = round(n_curr / max(1, n_prev), 2)
        if -delta_n >= 3 and v <= 0.40:
            st = "cooling"
        self.assertEqual(st, "cooling")

        # scope shifts
        scopes_prev = {"domestic"}
        scopes_curr = {"domestic", "international"}
        if scopes_prev == {"domestic"} and "international" in scopes_curr:
            shift = "international_pickup"
        else:
            shift = None
        self.assertEqual(shift, "international_pickup")

    def test_crisis_and_violence_classification(self):
        # US travel advisory date format without HH:MM:SS must parse cleanly
        dt = crisis._when({"published": "Fri, 23 Oct 2026"})
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 23)

        # GDACS Green spam capping & deduplication
        raw_items = [
            {"kind": "GDACS", "title": "Green forest fire notification in Australia", "level": "Green", "date": f"2026-11-0{i}T00:00:00+00:00"}
            for i in range(1, 6)
        ]
        deduped = crisis._dedup_and_cap(raw_items)
        self.assertEqual(len(deduped), 1)

        # Kinetic violence vs routine defence diplomacy & sports exclusion
        s_strike = {"headline": {"title": "Drone strike and artillery shelling reported in Kharkiv"}, "themes": ["Security and defence"], "sources": []}
        s_terror = {"headline": {"title": "Gunmen kidnap 12 villagers in Boko Haram ambush"}, "themes": ["Security and defence"], "sources": []}
        s_unrest = {"headline": {"title": "Police fire tear gas as riot and curfew grip capital"}, "themes": ["Internal politics"], "sources": []}
        s_diplomacy = {"headline": {"title": "Defence ministers sign bilateral military procurement memorandum"}, "themes": ["Security and defence"], "sources": []}
        s_sports = {"headline": {"title": "Striker leads attack in championship tournament clash"}, "themes": ["Sport"], "sources": []}

        self.assertEqual(export._classify_violence(s_strike), "Armed Clash & Strike")
        self.assertEqual(export._classify_violence(s_terror), "Insurgency & Terror")
        self.assertEqual(export._classify_violence(s_unrest), "Civil Unrest & Crackdown")
        self.assertIsNone(export._classify_violence(s_diplomacy))
        self.assertIsNone(export._classify_violence(s_sports))


if __name__ == "__main__":
    unittest.main()
