"""Tests for trajectory artifact with per-observation global_id integration.

These tests verify:
1. build_trajectory_artifact accepts optional global_id mapping
2. Each observation receives the correct global_id from the mapping
3. track_id remains unchanged
4. Existing observation fields remain unchanged
5. Multiple track_ids can share the same global_id
6. No GT_XXX values appear in runtime trajectories
7. Unresolved/provisional semantics are preserved
8. Trajectory ordering remains deterministic
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import build_trajectory_artifact


class TrajectoryGlobalIdIntegrationTests(unittest.TestCase):
    """Test per-observation global_id in trajectory artifact."""

    def test_build_trajectory_without_global_id(self):
        """Test backward compatibility: trajectory works without global_id mapping."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
                {"frame_id": 2, "timestamp": 0.133, "bbox": [105, 105, 205, 205],
                 "class": 1, "confidence": 0.9, "cx": 155.0, "cy": 155.0},
            ],
        }
        artifact = build_trajectory_artifact(track_observations)

        self.assertEqual(1, len(artifact["trajectories"]))
        traj = artifact["trajectories"][0]
        self.assertEqual(1, traj["track_id"])
        # global_id should be None when not provided
        for obs in traj["observations"]:
            self.assertIsNone(obs.get("global_id"))

    def test_build_trajectory_with_global_id_mapping(self):
        """Test that global_id is added to each observation."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
                {"frame_id": 2, "timestamp": 0.133, "bbox": [105, 105, 205, 205],
                 "class": 1, "confidence": 0.9, "cx": 155.0, "cy": 155.0},
            ],
        }
        track_id_to_global_id = {1: "G001"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        traj = artifact["trajectories"][0]
        for obs in traj["observations"]:
            self.assertEqual("G001", obs["global_id"])

    def test_track_id_unchanged(self):
        """Verify track_id remains the primary trajectory key."""
        track_observations = {
            5: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
        }
        track_id_to_global_id = {5: "G001"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        traj = artifact["trajectories"][0]
        self.assertEqual(5, traj["track_id"])
        self.assertEqual("G001", traj["observations"][0]["global_id"])

    def test_existing_fields_preserved(self):
        """Verify all existing observation fields remain unchanged."""
        track_observations = {
            1: [
                {"frame_id": 10, "timestamp": 0.667, "bbox": [50, 60, 150, 160],
                 "class": 2, "confidence": 0.85, "cx": 100.0, "cy": 110.0},
            ],
        }
        track_id_to_global_id = {1: "G002"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        obs = artifact["trajectories"][0]["observations"][0]
        self.assertEqual(10, obs["frame_id"])
        self.assertEqual(0.667, obs["timestamp"])
        self.assertEqual([50, 60, 150, 160], obs["bbox"])
        self.assertEqual(2, obs["class"])
        self.assertEqual(0.85, obs["confidence"])
        self.assertEqual(100.0, obs["cx"])
        self.assertEqual(110.0, obs["cy"])
        self.assertEqual("G002", obs["global_id"])

    def test_multiple_track_ids_share_same_global_id(self):
        """Test that multiple track_ids can map to the same global_id (MATCH case)."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
            2: [
                {"frame_id": 50, "timestamp": 3.333, "bbox": [300, 100, 400, 200],
                 "class": 1, "confidence": 0.9, "cx": 350.0, "cy": 150.0},
            ],
        }
        # Both track_id 1 and 2 are associated with the same global_id
        track_id_to_global_id = {1: "G001", 2: "G001"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        # Sort by track_id for deterministic check
        trajs = sorted(artifact["trajectories"], key=lambda t: t["track_id"])

        self.assertEqual(2, len(trajs))
        self.assertEqual(1, trajs[0]["track_id"])
        self.assertEqual("G001", trajs[0]["observations"][0]["global_id"])
        self.assertEqual(2, trajs[1]["track_id"])
        self.assertEqual("G001", trajs[1]["observations"][0]["global_id"])

    def test_different_global_ids_for_different_tracks(self):
        """Test that different track_ids can have different global_ids."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
            2: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [500, 100, 600, 200],
                 "class": 2, "confidence": 0.9, "cx": 550.0, "cy": 150.0},
            ],
        }
        track_id_to_global_id = {1: "G001", 2: "G002"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        trajs = {t["track_id"]: t for t in artifact["trajectories"]}
        self.assertEqual("G001", trajs[1]["observations"][0]["global_id"])
        self.assertEqual("G002", trajs[2]["observations"][0]["global_id"])

    def test_no_gt_in_runtime_trajectory(self):
        """Verify no GT_XXX values appear in runtime trajectory."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
        }
        # Simulate runtime global_ids (G001 format, not GT_XXX)
        track_id_to_global_id = {1: "G001"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        # Check no GT_XXX appears
        import json
        artifact_str = json.dumps(artifact)
        self.assertNotIn("GT_", artifact_str)
        self.assertIn("G001", artifact_str)

    def test_deterministic_trajectory_ordering(self):
        """Verify trajectory ordering remains deterministic."""
        track_observations = {
            3: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
            1: [
                {"frame_id": 2, "timestamp": 0.133, "bbox": [200, 200, 300, 300],
                 "class": 1, "confidence": 0.9, "cx": 250.0, "cy": 250.0},
            ],
            2: [
                {"frame_id": 3, "timestamp": 0.2, "bbox": [300, 300, 400, 400],
                 "class": 1, "confidence": 0.9, "cx": 350.0, "cy": 350.0},
            ],
        }
        track_id_to_global_id = {1: "G001", 2: "G002", 3: "G003"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        # Should be sorted by track_id
        track_ids = [t["track_id"] for t in artifact["trajectories"]]
        self.assertEqual([1, 2, 3], track_ids)

    def test_empty_track_id_to_global_id_mapping(self):
        """Test with empty global_id mapping - all observations get None."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
        }
        track_id_to_global_id = {}  # Empty mapping

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        obs = artifact["trajectories"][0]["observations"][0]
        self.assertIsNone(obs["global_id"])

    def test_partial_global_id_coverage(self):
        """Test when only some track_ids have global_id mappings."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
            2: [
                {"frame_id": 2, "timestamp": 0.133, "bbox": [200, 200, 300, 300],
                 "class": 1, "confidence": 0.9, "cx": 250.0, "cy": 250.0},
            ],
        }
        # Only track_id 1 has a global_id
        track_id_to_global_id = {1: "G001"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        trajs = {t["track_id"]: t for t in artifact["trajectories"]}
        self.assertEqual("G001", trajs[1]["observations"][0]["global_id"])
        self.assertIsNone(trajs[2]["observations"][0]["global_id"])


class TrajectoryArtifactSchemaTests(unittest.TestCase):
    """Test trajectory artifact schema with global_id field."""

    def test_observation_schema_with_global_id(self):
        """Verify observation schema includes global_id field."""
        track_observations = {
            1: [
                {"frame_id": 1, "timestamp": 0.067, "bbox": [100, 100, 200, 200],
                 "class": 1, "confidence": 0.9, "cx": 150.0, "cy": 150.0},
            ],
        }
        track_id_to_global_id = {1: "G001"}

        artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)

        obs = artifact["trajectories"][0]["observations"][0]
        # Verify all expected keys exist
        expected_keys = {"frame_id", "timestamp", "bbox", "class", "confidence", "cx", "cy", "global_id"}
        self.assertEqual(expected_keys, set(obs.keys()))


if __name__ == "__main__":
    unittest.main()
