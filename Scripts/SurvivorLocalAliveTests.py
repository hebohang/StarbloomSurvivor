"""Headless filtering and reference checks for the native region-alive query."""

import importlib
import sys
import types
import unittest
from unittest.mock import patch


_query_rows = []
_query_arguments = None


def _query_radius(*args):
    global _query_arguments
    _query_arguments = args
    return list(_query_rows)


with patch.dict(sys.modules, {
        "HEngine": types.SimpleNamespace(QuerySurvivorAgentsInRadius=_query_radius),
        "SurvivorRuntimeAssets": types.SimpleNamespace(asset_path=lambda path: path),
}):
    Objectives = importlib.import_module("SurvivorObjectives")


class LocalAliveContracts(unittest.TestCase):
    def setUp(self):
        global _query_rows, _query_arguments
        _query_rows = []
        _query_arguments = None
        self.game = Objectives.SurvivorObjectivesMixin()
        self.game.region_anchors = {
            "wind": (None, types.SimpleNamespace(Translation=types.SimpleNamespace(
                x=10.0, z=-5.0))),
        }
        self.game.monsters_by_id = {}
        self.game.monsters = []

    def test_filters_generation_death_encounter_and_missing_id(self):
        global _query_rows
        self.game.monsters_by_id = {
            1: {"activation_id": 7, "encounter_id": "region:wind", "dead": False},
            2: {"activation_id": 8, "encounter_id": "region:wind", "dead": False},
            3: {"activation_id": 9, "encounter_id": "region:star", "dead": False},
            4: {"activation_id": 10, "encounter_id": "region:wind", "dead": True},
        }
        _query_rows = [(0.0, 1, 7), (0.0, 2, 99), (0.0, 3, 9),
                       (0.0, 4, 10), (0.0, 5, 11)]
        self.assertEqual(self.game._local_region_alive("wind"), 1)
        self.assertEqual(_query_arguments[:4], (
            10.0, 0.0, -5.0, Objectives.OBJECTIVE_CONFIG["localAliveRadius"],
        ))
        self.assertGreater(_query_arguments[4], 3.4e38)

    def test_reference_mode_catches_native_count_mismatch(self):
        global _query_rows
        self.game.encounter_director = Objectives.EncounterDirector()
        self.game.monsters = [{
            "dead": False,
            "encounter_id": "region:wind",
            "transform": types.SimpleNamespace(Translation=types.SimpleNamespace(
                x=10.0, z=-5.0)),
        }]
        _query_rows = []
        with patch.object(Objectives, "_LOCAL_ALIVE_VERIFY", True):
            with self.assertRaisesRegex(AssertionError, "differs from reference"):
                self.game._local_region_alive("wind")


if __name__ == "__main__":
    unittest.main()
