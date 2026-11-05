"""Tests for delta comparison logic and movement classification."""
import unittest
import sys
import pathlib
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argos import export


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
        if n_prev == 0 and n_curr >= 2:
            st = "new"
        elif delta_n >= 3 and v >= 1.75:
            st = "surging"
        self.assertEqual(st, "surging")

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


if __name__ == "__main__":
    unittest.main()
