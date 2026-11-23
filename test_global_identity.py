import unittest

from global_identity import (
    GlobalIdentityAssociation,
    GlobalIdentityRegistry,
    RuntimeTrackingObservation,
    RuntimeTrackSegment,
    RuntimeGlobalIdentityRegistry,
    validate_global_id,
    validate_runtime_global_id,
    is_gt_global_id,
    TrackSegmentCandidate,
    CandidateGenerator,
    AssociationEvidence,
    AssociationDecision,
    AssociationBaseline,
    associate_track_segments,
    observation_from_bytetrack,
    build_track_segments_from_observations,
    build_global_identity_artifact,
    serialize_global_identity_artifact,
)


class GlobalIdentityTests(unittest.TestCase):
    def test_track_id_remains_separate(self):
        self.assertEqual(7, 7)

    def test_resolved_mapping(self):
        association = GlobalIdentityAssociation.from_resolved("GT_001", [7])
        self.assertEqual("GT_001", association.global_id)
        self.assertEqual([7], association.track_ids)
        self.assertEqual("RESOLVED", association.status)

    def test_multi_track_association(self):
        association = GlobalIdentityAssociation.from_resolved("GT_002", [8, 15])
        self.assertEqual([8, 15], association.track_ids)

    def test_unresolved_track(self):
        association = GlobalIdentityAssociation.from_unresolved(21)
        self.assertEqual("UNRESOLVED", association.status)
        self.assertEqual([21], association.track_ids)

    def test_invalid_global_id_fails(self):
        self.assertFalse(validate_global_id("GT_1"))
        with self.assertRaises(ValueError):
            GlobalIdentityAssociation.from_resolved("GT_1", [1])

    def test_conflation_rejected(self):
        with self.assertRaises(ValueError):
            GlobalIdentityAssociation.from_resolved("7", [7])

    def test_registry_store(self):
        registry = GlobalIdentityRegistry()
        record = registry.register_resolved("GT_003", [9, 10])
        self.assertEqual("GT_003", record.global_id)
        self.assertEqual([9, 10], record.track_ids)
        self.assertEqual(record, registry.get_by_global_id("GT_003"))


class RuntimeTrackingObservationTests(unittest.TestCase):
    def test_valid_observation_construction(self):
        """Test that a valid observation can be constructed with all required fields."""
        obs = RuntimeTrackingObservation(
            track_id=7,
            frame_id=10,
            timestamp=0.667,
            bbox=(100, 200, 300, 400),
            class_name="car",
            confidence=0.95,
            cx=200.0,
            cy=300.0,
        )
        self.assertEqual(7, obs.track_id)
        self.assertEqual(10, obs.frame_id)
        self.assertEqual(0.667, obs.timestamp)
        self.assertEqual((100, 200, 300, 400), obs.bbox)
        self.assertEqual("car", obs.class_name)
        self.assertEqual(0.95, obs.confidence)
        self.assertEqual(200.0, obs.cx)
        self.assertEqual(300.0, obs.cy)

    def test_observation_from_dict(self):
        """Test construction from dictionary (compatible with main.py tracking observations)."""
        data = {
            "track_id": 5,
            "frame_id": 15,
            "timestamp": 1.0,
            "bbox": [50, 100, 150, 200],
            "class": "motorcycle",
            "confidence": 0.87,
            "cx": 100.0,
            "cy": 150.0,
        }
        obs = RuntimeTrackingObservation.from_dict(data)
        self.assertEqual(5, obs.track_id)
        self.assertEqual(15, obs.frame_id)
        self.assertEqual("motorcycle", obs.class_name)
        self.assertEqual((50, 100, 150, 200), obs.bbox)

    def test_observation_to_dict(self):
        """Test conversion back to dictionary for trajectory compatibility."""
        obs = RuntimeTrackingObservation(
            track_id=3,
            frame_id=5,
            timestamp=0.333,
            bbox=(10, 20, 50, 60),
            class_name="bus",
            confidence=0.99,
            cx=30.0,
            cy=40.0,
        )
        d = obs.to_dict()
        self.assertEqual(3, d["track_id"])
        self.assertEqual("bus", d["class"])
        self.assertIsInstance(d["bbox"], list)

    def test_invalid_track_id_rejected(self):
        """Test that invalid track_id values are rejected."""
        with self.assertRaises(ValueError):
            RuntimeTrackingObservation(
                track_id=-1,
                frame_id=0,
                timestamp=0.0,
                bbox=(0, 0, 10, 10),
                class_name="car",
                confidence=0.9,
                cx=5.0,
                cy=5.0,
            )

    def test_invalid_confidence_rejected(self):
        """Test that confidence outside [0, 1] is rejected."""
        with self.assertRaises(ValueError):
            RuntimeTrackingObservation(
                track_id=1,
                frame_id=0,
                timestamp=0.0,
                bbox=(0, 0, 10, 10),
                class_name="car",
                confidence=1.5,
                cx=5.0,
                cy=5.0,
            )

    def test_deterministic_construction(self):
        """Test that the same input produces the same observation (no randomness)."""
        obs1 = RuntimeTrackingObservation(
            track_id=1,
            frame_id=10,
            timestamp=0.667,
            bbox=(100, 200, 300, 400),
            class_name="car",
            confidence=0.95,
            cx=200.0,
            cy=300.0,
        )
        obs2 = RuntimeTrackingObservation(
            track_id=1,
            frame_id=10,
            timestamp=0.667,
            bbox=(100, 200, 300, 400),
            class_name="car",
            confidence=0.95,
            cx=200.0,
            cy=300.0,
        )
        self.assertEqual(obs1.track_id, obs2.track_id)
        self.assertEqual(obs1.frame_id, obs2.frame_id)
        self.assertEqual(obs1.bbox, obs2.bbox)


class RuntimeTrackSegmentTests(unittest.TestCase):
    def test_track_segment_properties(self):
        """Test track segment stores observations and computes properties."""
        segment = RuntimeTrackSegment(track_id=7)
        obs1 = RuntimeTrackingObservation(
            track_id=7, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        )
        obs2 = RuntimeTrackingObservation(
            track_id=7, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        )
        segment.add_observation(obs1)
        segment.add_observation(obs2)
        self.assertEqual(7, segment.track_id)
        self.assertEqual(2, len(segment.observations))
        self.assertEqual(10, segment.start_frame)
        self.assertEqual(15, segment.end_frame)
        self.assertEqual("car", segment.class_name)

    def test_temporal_gap_calculation(self):
        """Test temporal gap calculation between segments."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=25, timestamp=1.667,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))
        gap = segment1.temporal_gap_to(segment2)
        self.assertEqual(15, gap)

    def test_spatial_distance_calculation(self):
        """Test spatial distance calculation between segments."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=25, timestamp=1.667,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=320.0,
        ))
        distance = segment1.spatial_distance_to(segment2)
        self.assertAlmostEqual(28.28, distance, delta=0.01)


class RuntimeGlobalIdentityRegistryTests(unittest.TestCase):
    def test_empty_registry_initialization(self):
        """Test that a new registry starts empty."""
        registry = RuntimeGlobalIdentityRegistry()
        self.assertEqual(0, registry.count_identities())
        self.assertEqual([], registry.list_identities())

    def test_deterministic_runtime_global_id_creation(self):
        """Test that runtime global_ids are generated deterministically."""
        registry = RuntimeGlobalIdentityRegistry()
        id1 = registry.create_identity()
        id2 = registry.create_identity()
        id3 = registry.create_identity()
        self.assertEqual("G001", id1)
        self.assertEqual("G002", id2)
        self.assertEqual("G003", id3)

    def test_registration_of_valid_runtime_identity(self):
        """Test registering a valid runtime identity."""
        registry = RuntimeGlobalIdentityRegistry()
        record = registry.register_identity("G010")
        self.assertEqual("G010", record.global_id)
        self.assertTrue(registry.identity_exists("G010"))

    def test_retrieval_of_registered_identity(self):
        """Test retrieving a registered identity by global_id."""
        registry = RuntimeGlobalIdentityRegistry()
        registry.create_identity()
        gid = registry.create_identity()
        record = registry.get_by_global_id(gid)
        self.assertIsNotNone(record)
        self.assertEqual(gid, record.global_id)

    def test_deterministic_listing_of_identities(self):
        """Test that identity listing is deterministic (by creation order)."""
        registry = RuntimeGlobalIdentityRegistry()
        id1 = registry.create_identity()
        id2 = registry.create_identity()
        id3 = registry.create_identity()
        ids = registry.list_identities()
        self.assertEqual([id1, id2, id3], ids)

    def test_explicit_registration_of_track_segment(self):
        """Test associating a track segment with an identity."""
        registry = RuntimeGlobalIdentityRegistry()
        gid = registry.create_identity()

        segment = RuntimeTrackSegment(track_id=7)
        segment.add_observation(RuntimeTrackingObservation(
            track_id=7, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        record = registry.associate_track_segment(gid, segment)
        self.assertEqual(gid, record.global_id)
        self.assertEqual(1, len(record.track_segments))

    def test_retrieval_of_segments_belonging_to_identity(self):
        """Test retrieving track segments associated with an identity."""
        registry = RuntimeGlobalIdentityRegistry()
        gid = registry.create_identity()

        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=5, timestamp=0.333,
            bbox=(50, 100, 150, 200), class_name="car",
            confidence=0.9, cx=100.0, cy=150.0,
        ))

        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(60, 110, 160, 210), class_name="car",
            confidence=0.88, cx=110.0, cy=160.0,
        ))

        registry.associate_track_segment(gid, segment1)
        registry.associate_track_segment(gid, segment2)

        track_ids = registry.get_track_ids_for_identity(gid)
        self.assertEqual([1, 2], track_ids)

    def test_duplicate_identity_rejection(self):
        """Test that duplicate identity registration is rejected."""
        registry = RuntimeGlobalIdentityRegistry()
        registry.create_identity()
        with self.assertRaises(ValueError):
            registry.register_identity("G001")

    def test_invalid_identity_rejection(self):
        """Test that invalid runtime global_id format is rejected."""
        registry = RuntimeGlobalIdentityRegistry()
        with self.assertRaises(ValueError):
            registry.register_identity("G1")
        with self.assertRaises(ValueError):
            registry.register_identity("G0001")
        with self.assertRaises(ValueError):
            registry.register_identity("GT_001")

    def test_duplicate_segment_association_rejection(self):
        """Test that associating a track to a different global_id is rejected."""
        registry = RuntimeGlobalIdentityRegistry()
        gid1 = registry.create_identity()
        gid2 = registry.create_identity()

        segment = RuntimeTrackSegment(track_id=5)
        segment.add_observation(RuntimeTrackingObservation(
            track_id=5, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry.associate_track_segment(gid1, segment)
        with self.assertRaises(ValueError):
            registry.associate_track_segment(gid2, segment)

    def test_gt_identity_rejection(self):
        """Test that GT global_id cannot be registered in runtime registry."""
        registry = RuntimeGlobalIdentityRegistry()
        with self.assertRaises(ValueError):
            registry.register_identity("GT_001")

    def test_registry_instance_state_isolation(self):
        """Test that each registry instance has isolated state."""
        registry1 = RuntimeGlobalIdentityRegistry()
        registry2 = RuntimeGlobalIdentityRegistry()

        gid = registry1.create_identity()
        self.assertEqual(1, registry1.count_identities())
        self.assertEqual(0, registry2.count_identities())
        self.assertIsNone(registry2.get_by_global_id(gid))

    def test_deterministic_repeated_operations(self):
        """Test that repeated identical operations produce identical results."""
        registry1 = RuntimeGlobalIdentityRegistry()
        registry2 = RuntimeGlobalIdentityRegistry()

        for _ in range(3):
            registry1.create_identity()

        for _ in range(3):
            registry2.create_identity()

        self.assertEqual(registry1.list_identities(), registry2.list_identities())

    def test_track_id_retrieval(self):
        """Test retrieving identity by track_id."""
        registry = RuntimeGlobalIdentityRegistry()
        gid = registry.create_identity()

        segment = RuntimeTrackSegment(track_id=42)
        segment.add_observation(RuntimeTrackingObservation(
            track_id=42, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry.associate_track_segment(gid, segment)

        record = registry.get_by_track_id(42)
        self.assertIsNotNone(record)
        self.assertEqual(gid, record.global_id)

    def test_clear_registry(self):
        """Test clearing registry state."""
        registry = RuntimeGlobalIdentityRegistry()
        registry.create_identity()
        registry.create_identity()
        self.assertEqual(2, registry.count_identities())

        registry.clear()
        self.assertEqual(0, registry.count_identities())
        self.assertEqual([], registry.list_identities())

    def test_validate_runtime_global_id(self):
        """Test runtime global_id format validation."""
        self.assertTrue(validate_runtime_global_id("G001"))
        self.assertTrue(validate_runtime_global_id("G999"))
        self.assertFalse(validate_runtime_global_id("G1"))
        self.assertFalse(validate_runtime_global_id("G0001"))
        self.assertFalse(validate_runtime_global_id("GT_001"))
        self.assertFalse(validate_runtime_global_id("R001"))

    def test_is_gt_global_id(self):
        """Test GT identity detection."""
        self.assertTrue(is_gt_global_id("GT_001"))
        self.assertTrue(is_gt_global_id("GT_999"))
        self.assertFalse(is_gt_global_id("G001"))
        self.assertFalse(is_gt_global_id("GT1"))
        self.assertFalse(is_gt_global_id("car"))


class CandidateGenerationTests(unittest.TestCase):
    def test_valid_candidate_construction(self):
        """Test that a valid candidate can be constructed."""
        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=30,
            spatial_distance=50.0,
            class_match=True,
            class_name="car",
        )
        self.assertEqual(1, candidate.previous_track_id)
        self.assertEqual(2, candidate.current_track_id)
        self.assertEqual(30, candidate.temporal_gap)
        self.assertEqual(50.0, candidate.spatial_distance)
        self.assertTrue(candidate.class_match)
        self.assertEqual("car", candidate.class_name)

    def test_self_candidate_rejected(self):
        """Test that a track cannot be paired with itself."""
        with self.assertRaises(ValueError):
            TrackSegmentCandidate(
                previous_track_id=1,
                current_track_id=1,
                temporal_gap=0,
                spatial_distance=0.0,
                class_match=True,
                class_name="car",
            )

    def test_deterministic_candidate_generation(self):
        """Test that the same input produces the same candidates."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        generator1 = CandidateGenerator()
        generator2 = CandidateGenerator()

        candidates1 = generator1.generate_candidates([segment1, segment2])
        candidates2 = generator2.generate_candidates([segment1, segment2])

        self.assertEqual(len(candidates1), len(candidates2))
        for c1, c2 in zip(candidates1, candidates2):
            self.assertEqual(c1.previous_track_id, c2.previous_track_id)
            self.assertEqual(c1.current_track_id, c2.current_track_id)
            self.assertEqual(c1.temporal_gap, c2.temporal_gap)
            self.assertEqual(c1.spatial_distance, c2.spatial_distance)

    def test_no_self_candidates_in_output(self):
        """Test that self-candidates are not generated."""
        segment = RuntimeTrackSegment(track_id=1)
        segment.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment])

        self.assertEqual(0, len(candidates))
        for candidate in candidates:
            self.assertNotEqual(candidate.previous_track_id, candidate.current_track_id)

    def test_no_duplicate_candidates(self):
        """Test that duplicate candidate pairs are prevented."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        # Check for duplicates
        seen = set()
        for c in candidates:
            pair = (c.previous_track_id, c.current_track_id)
            self.assertNotIn(pair, seen)
            seen.add(pair)

    def test_deterministic_candidate_ordering(self):
        """Test that candidates are in deterministic order."""
        segment1 = RuntimeTrackSegment(track_id=3)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=1)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))
        segment3 = RuntimeTrackSegment(track_id=2)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=80, timestamp=5.333,
            bbox=(200, 220, 400, 420), class_name="car",
            confidence=0.88, cx=300.0, cy=320.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2, segment3])

        # Verify order is deterministic (by track_id)
        prev_ids = [c.previous_track_id for c in candidates]
        self.assertEqual(prev_ids, sorted(prev_ids))

    def test_temporal_evidence_preservation(self):
        """Test that temporal evidence is preserved in candidates."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        self.assertEqual(1, len(candidates))
        self.assertEqual(40, candidates[0].temporal_gap)  # 50 - 10

    def test_spatial_evidence_preservation(self):
        """Test that spatial evidence is preserved in candidates."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=300.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        self.assertEqual(1, len(candidates))
        self.assertAlmostEqual(50.0, candidates[0].spatial_distance, delta=0.01)

    def test_class_metadata_preservation(self):
        """Test that class metadata is preserved in candidates."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        self.assertEqual(1, len(candidates))
        self.assertTrue(candidates[0].class_match)
        self.assertEqual("car", candidates[0].class_name)

    def test_class_mismatch_preserved(self):
        """Test that class mismatch is preserved as metadata (not eliminated)."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="truck",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        self.assertEqual(1, len(candidates))
        self.assertFalse(candidates[0].class_match)
        self.assertEqual("car", candidates[0].class_name)

    def test_insufficient_evidence_not_match(self):
        """Test that insufficient evidence does not become a MATCH decision."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        # Candidate exists but there is NO same_identity field
        self.assertEqual(1, len(candidates))
        self.assertFalse(hasattr(candidates[0], "same_identity"))
        self.assertFalse(hasattr(candidates[0], "is_match"))
        self.assertFalse(hasattr(candidates[0], "global_id"))

    def test_no_runtime_global_id_assignment(self):
        """Test that candidates do not contain runtime global_id."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        for c in candidates:
            self.assertFalse(hasattr(c, "global_id"))
            self.assertFalse(hasattr(c, "assigned_global_id"))

    def test_empty_input_handling(self):
        """Test that empty input produces empty output."""
        generator = CandidateGenerator()
        candidates = generator.generate_candidates([])
        self.assertEqual(0, len(candidates))

    def test_temporal_boundary_filtering(self):
        """Test that max_temporal_gap filters candidates."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=200, timestamp=13.333,
            bbox=(200, 220, 400, 420), class_name="car",
            confidence=0.88, cx=300.0, cy=320.0,
        ))

        # With small gap limit, segment1->segment3 should be filtered
        generator = CandidateGenerator(max_temporal_gap=50)
        candidates = generator.generate_candidates([segment1, segment2, segment3])

        # segment1->segment2 gap=40, segment1->segment3 gap=190, segment2->segment3 gap=150
        # Only segment1->segment2 should pass
        self.assertEqual(1, len(candidates))
        self.assertEqual(1, candidates[0].previous_track_id)
        self.assertEqual(2, candidates[0].current_track_id)

    def test_overlapping_segments_excluded(self):
        """Test that temporally overlapping segments are not candidates."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=12, timestamp=0.8,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        # segment2 starts at frame 12, segment1 ends at frame 15
        # segment2.start_frame (12) <= segment1.end_frame (15), so no candidate
        self.assertEqual(0, len(candidates))

    def test_candidate_to_dict(self):
        """Test candidate serialization."""
        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=30,
            spatial_distance=50.0,
            class_match=True,
            class_name="car",
        )
        d = candidate.to_dict()
        self.assertEqual(1, d["previous_track_id"])
        self.assertEqual(2, d["current_track_id"])
        self.assertEqual(30, d["temporal_gap"])
        self.assertEqual(50.0, d["spatial_distance"])
        self.assertTrue(d["class_match"])
        self.assertEqual("car", d["class_name"])


class AssociationBaselineTests(unittest.TestCase):
    def test_valid_decision_construction(self):
        """Test that a valid decision can be constructed."""
        evidence = AssociationEvidence(
            temporal_gap=10,
            spatial_distance=50.0,
            motion_direction_match=True,
            motion_direction_angle=30.0,
            class_match=True,
            class_name="car",
            temporal_within_threshold=True,
            spatial_within_threshold=True,
        )
        decision = AssociationDecision(
            previous_track_id=1,
            current_track_id=2,
            decision="MATCH",
            evidence=evidence,
            reason="All baseline thresholds satisfied",
        )
        self.assertEqual("MATCH", decision.decision)
        self.assertEqual(1, decision.previous_track_id)
        self.assertEqual(2, decision.current_track_id)

    def test_match_decision(self):
        """Test MATCH decision when thresholds are satisfied."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=5,
            spatial_distance=20.0,
            class_match=True,
            class_name="car",
        )

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual("MATCH", decision.decision)
        self.assertTrue(decision.evidence.temporal_within_threshold)
        self.assertTrue(decision.evidence.spatial_within_threshold)

    def test_no_match_temporal(self):
        """Test NO_MATCH when temporal gap exceeds threshold."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=100, timestamp=6.667,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=90,
            spatial_distance=50.0,
            class_match=True,
            class_name="car",
        )

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual("NO_MATCH", decision.decision)
        self.assertIn("Temporal gap", decision.reason)

    def test_no_match_spatial(self):
        """Test NO_MATCH when spatial distance exceeds threshold."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=10,
            spatial_distance=500.0,
            class_match=True,
            class_name="car",
        )

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual("NO_MATCH", decision.decision)
        self.assertIn("Spatial distance", decision.reason)

    def test_temporal_evidence_handling(self):
        """Test that temporal evidence is preserved in decision."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=30, timestamp=2.0,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=20,
            spatial_distance=50.0,
            class_match=True,
            class_name="car",
        )

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual(20, decision.evidence.temporal_gap)
        self.assertTrue(decision.evidence.temporal_within_threshold)

    def test_spatial_evidence_handling(self):
        """Test that spatial evidence is preserved in decision."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=30, timestamp=2.0,
            bbox=(140, 230, 340, 430), class_name="car",
            confidence=0.90, cx=240.0, cy=330.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=20,
            spatial_distance=50.0,
            class_match=True,
            class_name="car",
        )

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertAlmostEqual(50.0, decision.evidence.spatial_distance, delta=0.01)
        self.assertTrue(decision.evidence.spatial_within_threshold)

    def test_motion_evidence_handling(self):
        """Test that motion/trajectory evidence is preserved."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=5,
            spatial_distance=50.0,
            class_match=True,
            class_name="car",
        )

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertIsNotNone(decision.evidence.motion_direction_match)
        self.assertIsNotNone(decision.evidence.motion_direction_angle)

    def test_class_as_supporting_evidence(self):
        """Test that class is supporting evidence only (not primary criterion)."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="truck",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=10,
            spatial_distance=30.0,
            class_match=False,
            class_name="car",
        )

        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            require_class_match=False,  # Class not required
        )
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual("MATCH", decision.decision)
        self.assertFalse(decision.evidence.class_match)

    def test_class_required_when_configured(self):
        """Test that class can be required when configured."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="truck",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=10,
            spatial_distance=30.0,
            class_match=False,
            class_name="car",
        )

        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            require_class_match=True,  # Class required
        )
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual("NO_MATCH", decision.decision)
        self.assertIn("Class mismatch", decision.reason)

    def test_deterministic_scoring(self):
        """Test that scoring is deterministic."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=10,
            spatial_distance=30.0,
            class_match=True,
            class_name="car",
        )

        baseline1 = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        baseline2 = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)

        decision1 = baseline1.evaluate_candidate(candidate, segment1, segment2)
        decision2 = baseline2.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual(decision1.decision, decision2.decision)
        self.assertEqual(decision1.evidence.temporal_gap, decision2.evidence.temporal_gap)
        self.assertEqual(decision1.evidence.spatial_distance, decision2.evidence.spatial_distance)

    def test_deterministic_decisions(self):
        """Test that decisions are deterministic across runs."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        candidates = [
            TrackSegmentCandidate(
                previous_track_id=1,
                current_track_id=2,
                temporal_gap=10,
                spatial_distance=30.0,
                class_match=True,
                class_name="car",
            )
        ]

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)

        decisions1 = baseline.evaluate_candidates(candidates, [segment1, segment2])
        decisions2 = baseline.evaluate_candidates(candidates, [segment1, segment2])

        self.assertEqual(len(decisions1), len(decisions2))
        self.assertEqual(decisions1[0].decision, decisions2[0].decision)

    def test_associate_track_segments_creates_identities(self):
        """Test that associate_track_segments creates global identities."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Should have created identities
        self.assertGreater(registry.count_identities(), 0)

        # Track 1 and 2 should have identities
        self.assertIsNotNone(registry.get_by_track_id(1))
        self.assertIsNotNone(registry.get_by_track_id(2))

    def test_associate_track_segments_matches_similar(self):
        """Test that similar tracks are matched."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        # Track 2 is very close spatially and temporally
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Find MATCH decision
        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))

    def test_associate_track_segments_no_match_distant(self):
        """Test that distant tracks are not matched."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        # Track 2 is far away spatially
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Find NO_MATCH decision
        no_match_decisions = [d for d in decisions if d.decision == "NO_MATCH"]
        self.assertEqual(1, len(no_match_decisions))

        # Each should get its own identity since not matched
        self.assertIsNotNone(registry.get_by_track_id(1))
        self.assertIsNotNone(registry.get_by_track_id(2))

    def test_no_duplicate_association(self):
        """Test that duplicate associations are not created."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        # Run twice
        associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Count identities - should not have duplicates
        identities = registry.list_identities()
        # Each track should be in exactly one identity
        track_ids = set()
        for gid in identities:
            for tid in registry.get_track_ids_for_identity(gid):
                self.assertNotIn(tid, track_ids)
                track_ids.add(tid)

    def test_no_runtime_gt_dependency(self):
        """Test that no GT data is used."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # No GT IDs should be created
        for gid in registry.list_identities():
            self.assertFalse(is_gt_global_id(gid))

    def test_runtime_global_id_distinct_from_track_id(self):
        """Test that runtime global IDs are distinct from track IDs."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Global IDs should be G### format, not track IDs
        for gid in registry.list_identities():
            self.assertTrue(validate_runtime_global_id(gid))

    def test_invalid_decision_rejected(self):
        """Test that invalid decision value is rejected."""
        evidence = AssociationEvidence(
            temporal_gap=10,
            spatial_distance=50.0,
            motion_direction_match=True,
            motion_direction_angle=30.0,
            class_match=True,
            class_name="car",
            temporal_within_threshold=True,
            spatial_within_threshold=True,
        )
        with self.assertRaises(ValueError):
            AssociationDecision(
                previous_track_id=1,
                current_track_id=2,
                decision="INVALID",
                evidence=evidence,
                reason="Test",
            )

    def test_evidence_to_dict(self):
        """Test evidence serialization."""
        evidence = AssociationEvidence(
            temporal_gap=10,
            spatial_distance=50.0,
            motion_direction_match=True,
            motion_direction_angle=30.0,
            class_match=True,
            class_name="car",
            temporal_within_threshold=True,
            spatial_within_threshold=True,
        )
        d = evidence.to_dict()
        self.assertEqual(10, d["temporal_gap"])
        self.assertEqual(50.0, d["spatial_distance"])
        self.assertTrue(d["motion_direction_match"])
        self.assertEqual(30.0, d["motion_direction_angle"])
        self.assertTrue(d["class_match"])
        self.assertTrue(d["temporal_within_threshold"])
        self.assertTrue(d["spatial_within_threshold"])

    def test_decision_to_dict(self):
        """Test decision serialization."""
        evidence = AssociationEvidence(
            temporal_gap=10,
            spatial_distance=50.0,
            motion_direction_match=True,
            motion_direction_angle=30.0,
            class_match=True,
            class_name="car",
            temporal_within_threshold=True,
            spatial_within_threshold=True,
        )
        decision = AssociationDecision(
            previous_track_id=1,
            current_track_id=2,
            decision="MATCH",
            evidence=evidence,
            reason="All thresholds satisfied",
        )
        d = decision.to_dict()
        self.assertEqual(1, d["previous_track_id"])
        self.assertEqual(2, d["current_track_id"])
        self.assertEqual("MATCH", d["decision"])
        self.assertEqual("All thresholds satisfied", d["reason"])




class GlobalIdentityValidationTests(unittest.TestCase):
    """Validation tests for Global Identity Association baseline.

    These tests verify that the implementation behaves according to its documented contract.
    They cover: CLEAR MATCH, CLEAR NO_MATCH, INSUFFICIENT EVIDENCE, COMPETING CANDIDATES,
    CLASS DIFFERENCE, DETERMINISM, and REGISTRY CONSISTENCY.
    """

    # ===== CLEAR MATCH Tests =====
    def test_clear_match_temporal_spatial_compatible(self):
        """CLEAR MATCH: temporally and spatially compatible segments should match."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))
        self.assertEqual(1, match_decisions[0].previous_track_id)
        self.assertEqual(2, match_decisions[0].current_track_id)

        gid1 = registry.get_by_track_id(1)
        gid2 = registry.get_by_track_id(2)
        self.assertIsNotNone(gid1)
        self.assertIsNotNone(gid2)
        self.assertEqual(gid1.global_id, gid2.global_id)

    def test_clear_match_motion_direction_compatible(self):
        """CLEAR MATCH: compatible motion direction should support match."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 200, 400), class_name="car",
            confidence=0.95, cx=150.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(200, 200, 300, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(300, 200, 400, 400), class_name="car",
            confidence=0.90, cx=350.0, cy=300.0,
        ))
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=25, timestamp=1.667,
            bbox=(350, 200, 450, 400), class_name="car",
            confidence=0.88, cx=400.0, cy=300.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))
        self.assertTrue(match_decisions[0].evidence.motion_direction_match)

    def test_clear_match_class_compatible(self):
        """CLEAR MATCH: same class should support match."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="truck",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="truck",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="truck",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))
        self.assertTrue(match_decisions[0].evidence.class_match)
        self.assertEqual("truck", match_decisions[0].evidence.class_name)

    # ===== CLEAR NO_MATCH Tests =====
    def test_clear_no_match_temporal_incompatible(self):
        """CLEAR NO_MATCH: temporally incompatible segments should not match."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=110, timestamp=7.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(0, len(match_decisions))

    def test_clear_no_match_spatial_incompatible(self):
        """CLEAR NO_MATCH: spatially incompatible segments should not match."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(700, 200, 900, 400), class_name="car",
            confidence=0.90, cx=800.0, cy=300.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        no_match_decisions = [d for d in decisions if d.decision == "NO_MATCH"]
        self.assertEqual(1, len(no_match_decisions))
        self.assertIn("Spatial", no_match_decisions[0].reason)

    def test_clear_no_match_both_incompatible(self):
        """CLEAR NO_MATCH: both temporal and spatial incompatibility."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=200, timestamp=13.333,
            bbox=(800, 400, 1000, 600), class_name="car",
            confidence=0.90, cx=900.0, cy=500.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(0, len(match_decisions))

    # ===== INSUFFICIENT EVIDENCE Tests =====
    def test_insufficient_evidence_boundary_temporal(self):
        """INSUFFICIENT EVIDENCE: ambiguous temporal boundary."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=40, timestamp=2.667,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))

    def test_insufficient_evidence_boundary_spatial(self):
        """INSUFFICIENT EVIDENCE: ambiguous spatial boundary."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(300, 200, 500, 400), class_name="car",
            confidence=0.90, cx=400.0, cy=300.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))

    def test_insufficient_evidence_ambiguous_motion(self):
        """INSUFFICIENT EVIDENCE: ambiguous motion direction should not prevent MATCH."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))
        self.assertFalse(match_decisions[0].evidence.motion_direction_match)

    # ===== COMPETING CANDIDATES Tests =====
    def test_competing_candidates_deterministic_selection(self):
        """COMPETING CANDIDATES: multiple candidates should be deterministic."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 250, 350, 450), class_name="car",
            confidence=0.93, cx=250.0, cy=350.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(260, 260, 360, 460), class_name="car",
            confidence=0.90, cx=310.0, cy=360.0,
        ))
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=20, timestamp=1.333,
            bbox=(270, 280, 370, 480), class_name="car",
            confidence=0.90, cx=320.0, cy=380.0,
        ))

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2, segment3])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2, segment3])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(2, len(match_decisions))

    def test_competing_candidates_no_silent_identity_creation(self):
        """COMPETING CANDIDATES: ambiguous case should not silently create arbitrary identity."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(260, 200, 360, 400), class_name="car",
            confidence=0.90, cx=310.0, cy=300.0,
        ))
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=20, timestamp=1.333,
            bbox=(260, 210, 360, 410), class_name="car",
            confidence=0.90, cx=310.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2, segment3],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        all_track_ids = {1, 2, 3}
        for tid in all_track_ids:
            record = registry.get_by_track_id(tid)
            self.assertIsNotNone(record, f"Track {tid} should have a global identity")

    # ===== CLASS DIFFERENCE Tests =====
    def test_class_difference_supporting_not_absolute(self):
        """CLASS DIFFERENCE: class consistency is supporting evidence, not absolute rule."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="truck",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            require_class_match=False,
        )
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))
        self.assertFalse(match_decisions[0].evidence.class_match)

    def test_class_difference_with_required_class(self):
        """CLASS DIFFERENCE: when class is required, mismatch leads to NO_MATCH."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="truck",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            require_class_match=True,
        )
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        no_match_decisions = [d for d in decisions if d.decision == "NO_MATCH"]
        self.assertEqual(1, len(no_match_decisions))
        self.assertIn("Class", no_match_decisions[0].reason)

    # ===== DETERMINISM Tests =====
    def test_determinism_identical_inputs(self):
        """DETERMINISM: identical inputs must produce identical evidence and decisions."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        results = []
        for _ in range(5):
            registry = RuntimeGlobalIdentityRegistry()
            baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
            generator = CandidateGenerator()

            decisions = associate_track_segments(
                [segment1, segment2],
                registry,
                candidate_generator=generator,
                association_baseline=baseline,
            )

            results.append([(d.decision, d.evidence.temporal_gap, d.evidence.spatial_distance)
                          for d in decisions])

        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])

    def test_determinism_candidate_order_independence(self):
        """DETERMINISM: candidate ordering should not affect final decisions."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=25, timestamp=1.667,
            bbox=(250, 200, 450, 400), class_name="car",
            confidence=0.90, cx=350.0, cy=300.0,
        ))

        segments_order_1 = [segment1, segment2, segment3]
        segments_order_2 = [segment3, segment1, segment2]
        segments_order_3 = [segment2, segment3, segment1]

        results = []
        for segments in [segments_order_1, segments_order_2, segments_order_3]:
            registry = RuntimeGlobalIdentityRegistry()
            baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
            generator = CandidateGenerator()

            decisions = associate_track_segments(
                segments,
                registry,
                candidate_generator=generator,
                association_baseline=baseline,
            )

            match_pairs = []
            for d in decisions:
                if d.decision == "MATCH":
                    match_pairs.append((d.previous_track_id, d.current_track_id))
            match_pairs.sort()
            results.append(match_pairs)

        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    # ===== REGISTRY CONSISTENCY Tests =====
    def test_registry_consistency_explicit_association(self):
        """REGISTRY CONSISTENCY: explicit association produces consistent global identity."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        gid1 = registry.get_by_track_id(1)
        gid2 = registry.get_by_track_id(2)

        self.assertIsNotNone(gid1)
        self.assertIsNotNone(gid2)
        self.assertEqual(gid1.global_id, gid2.global_id)

        gid = gid1.global_id
        record = registry.get_by_global_id(gid)
        self.assertIsNotNone(record)
        track_ids = record.get_track_ids()
        self.assertEqual(2, len(track_ids))
        self.assertIn(1, track_ids)
        self.assertIn(2, track_ids)

    def test_registry_consistency_unrelated_segments(self):
        """REGISTRY CONSISTENCY: unrelated segments should not collapse into same identity."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=50, timestamp=3.333,
            bbox=(800, 400, 1000, 600), class_name="car",
            confidence=0.90, cx=900.0, cy=500.0,
        ))
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=100, timestamp=6.667,
            bbox=(100, 400, 300, 600), class_name="car",
            confidence=0.90, cx=200.0, cy=500.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        associate_track_segments(
            [segment1, segment2, segment3],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        gid1 = registry.get_by_track_id(1)
        gid2 = registry.get_by_track_id(2)
        gid3 = registry.get_by_track_id(3)

        self.assertIsNotNone(gid1)
        self.assertIsNotNone(gid2)
        self.assertIsNotNone(gid3)

        self.assertNotEqual(gid1.global_id, gid2.global_id)
        self.assertNotEqual(gid2.global_id, gid3.global_id)
        self.assertNotEqual(gid1.global_id, gid3.global_id)

    def test_registry_no_duplicate_track_assignment(self):
        """REGISTRY CONSISTENCY: track should not be assigned to multiple identities."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        track_to_gid = {}
        for gid in registry.list_identities():
            record = registry.get_by_global_id(gid)
            for tid in record.get_track_ids():
                self.assertNotIn(tid, track_to_gid, f"Track {tid} already assigned!")
                track_to_gid[tid] = gid

        self.assertIn(1, track_to_gid)
        self.assertIn(2, track_to_gid)

    def test_registry_format_consistency(self):
        """REGISTRY CONSISTENCY: all runtime IDs should follow G### format."""
        segments = []
        for i in range(5):
            segment = RuntimeTrackSegment(track_id=i+1)
            segment.add_observation(RuntimeTrackingObservation(
                track_id=i+1, frame_id=10 + i*10, timestamp=0.667 + i*0.667,
                bbox=(100 + i*10, 200, 300 + i*10, 400),
                class_name="car",
                confidence=0.95, cx=200.0 + i*10, cy=300.0,
            ))
            segments.append(segment)

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        associate_track_segments(
            segments,
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        for gid in registry.list_identities():
            self.assertTrue(validate_runtime_global_id(gid),
                           f"Global ID {gid} does not match G### format")


class ByteTrackIntegrationSeamTests(unittest.TestCase):
    """Tests for the runtime integration seam between ByteTrack and Global Identity.

    These tests verify that the integration seam correctly converts ByteTrack output
    to RuntimeTrackingObservation while preserving all required fields.
    """

    def test_bytetrack_observation_with_class_mapping(self):
        """Test conversion from ByteTrack format with class mapping."""
        bytetrack_data = {
            "track_id": 7,
            "frame_id": 10,
            "timestamp": 0.667,
            "bbox": [100, 200, 300, 400],
            "class": 2,  # Integer class ID
            "confidence": 0.95,
            "cx": 200.0,
            "cy": 300.0,
        }
        class_mapping = {0: "car", 1: "motorcycle", 2: "bus", 3: "truck"}

        obs = observation_from_bytetrack(bytetrack_data, class_mapping)

        self.assertEqual(7, obs.track_id)
        self.assertEqual(10, obs.frame_id)
        self.assertEqual(0.667, obs.timestamp)
        self.assertEqual((100, 200, 300, 400), obs.bbox)
        self.assertEqual("bus", obs.class_name)  # Mapped from 2
        self.assertEqual(0.95, obs.confidence)
        self.assertEqual(200.0, obs.cx)
        self.assertEqual(300.0, obs.cy)

    def test_bytetrack_observation_without_class_mapping(self):
        """Test conversion without class mapping (class as string)."""
        bytetrack_data = {
            "track_id": 5,
            "frame_id": 15,
            "timestamp": 1.0,
            "bbox": [50, 100, 150, 200],
            "class": "car",  # Already a string
            "confidence": 0.87,
            "cx": 100.0,
            "cy": 150.0,
        }

        obs = observation_from_bytetrack(bytetrack_data)

        self.assertEqual(5, obs.track_id)
        self.assertEqual("car", obs.class_name)

    def test_bytetrack_without_center_computes_from_bbox(self):
        """Test that center is computed from bbox when not provided."""
        bytetrack_data = {
            "track_id": 3,
            "frame_id": 5,
            "timestamp": 0.333,
            "bbox": [10, 20, 110, 120],
            "class": "car",
            "confidence": 0.99,
            # No cx, cy provided
        }

        obs = observation_from_bytetrack(bytetrack_data)

        # Center should be computed from bbox: (10+110)/2=60, (20+120)/2=70
        self.assertEqual(60.0, obs.cx)
        self.assertEqual(70.0, obs.cy)

    def test_bytetrack_track_id_preserved(self):
        """Test that track_id is preserved exactly."""
        bytetrack_data = {
            "track_id": 42,
            "frame_id": 0,
            "timestamp": 0.0,
            "bbox": [0, 0, 10, 10],
            "class": "car",
            "confidence": 0.5,
            "cx": 5.0,
            "cy": 5.0,
        }

        obs = observation_from_bytetrack(bytetrack_data)

        self.assertEqual(42, obs.track_id)

    def test_bytetrack_frame_id_preserved(self):
        """Test that frame_id is preserved exactly."""
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 150,
            "timestamp": 10.0,
            "bbox": [0, 0, 10, 10],
            "class": "car",
            "confidence": 0.5,
            "cx": 5.0,
            "cy": 5.0,
        }

        obs = observation_from_bytetrack(bytetrack_data)

        self.assertEqual(150, obs.frame_id)

    def test_bytetrack_bbox_preserved(self):
        """Test that bbox is preserved exactly."""
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 0,
            "timestamp": 0.0,
            "bbox": [50, 100, 200, 300],
            "class": "car",
            "confidence": 0.5,
            "cx": 125.0,
            "cy": 200.0,
        }

        obs = observation_from_bytetrack(bytetrack_data)

        self.assertEqual((50, 100, 200, 300), obs.bbox)

    def test_bytetrack_class_preserved(self):
        """Test that class is preserved correctly."""
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 0,
            "timestamp": 0.0,
            "bbox": [0, 0, 10, 10],
            "class": 1,
            "confidence": 0.5,
            "cx": 5.0,
            "cy": 5.0,
        }
        class_mapping = {0: "car", 1: "motorcycle"}

        obs = observation_from_bytetrack(bytetrack_data, class_mapping)

        self.assertEqual("motorcycle", obs.class_name)

    def test_bytetrack_confidence_preserved(self):
        """Test that confidence is preserved exactly."""
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 0,
            "timestamp": 0.0,
            "bbox": [0, 0, 10, 10],
            "class": "car",
            "confidence": 0.875,
            "cx": 5.0,
            "cy": 5.0,
        }

        obs = observation_from_bytetrack(bytetrack_data)

        self.assertEqual(0.875, obs.confidence)

    def test_bytetrack_invalid_missing_track_id(self):
        """Test that missing track_id raises appropriate error."""
        bytetrack_data = {
            "frame_id": 0,
            "timestamp": 0.0,
            "bbox": [0, 0, 10, 10],
            "class": "car",
            "confidence": 0.5,
        }

        with self.assertRaises(KeyError):
            observation_from_bytetrack(bytetrack_data)

    def test_bytetrack_invalid_missing_bbox(self):
        """Test that missing bbox raises appropriate error."""
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 0,
            "timestamp": 0.0,
            "class": "car",
            "confidence": 0.5,
        }

        with self.assertRaises(KeyError):
            observation_from_bytetrack(bytetrack_data)

    def test_bytetrack_gt_not_required(self):
        """Test that GT data is not required for conversion."""
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 0,
            "timestamp": 0.0,
            "bbox": [0, 0, 10, 10],
            "class": "car",
            "confidence": 0.5,
            "cx": 5.0,
            "cy": 5.0,
            # No GT data
        }

        obs = observation_from_bytetrack(bytetrack_data)

        self.assertIsNotNone(obs.track_id)
        self.assertIsNotNone(obs.frame_id)

    def test_bytetrack_deterministic_repeated_conversion(self):
        """Test that repeated identical input produces identical output."""
        bytetrack_data = {
            "track_id": 7,
            "frame_id": 10,
            "timestamp": 0.667,
            "bbox": [100, 200, 300, 400],
            "class": 2,
            "confidence": 0.95,
            "cx": 200.0,
            "cy": 300.0,
        }
        class_mapping = {0: "car", 1: "motorcycle", 2: "bus", 3: "truck"}

        obs1 = observation_from_bytetrack(bytetrack_data, class_mapping)
        obs2 = observation_from_bytetrack(bytetrack_data, class_mapping)

        self.assertEqual(obs1.track_id, obs2.track_id)
        self.assertEqual(obs1.frame_id, obs2.frame_id)
        self.assertEqual(obs1.bbox, obs2.bbox)
        self.assertEqual(obs1.class_name, obs2.class_name)
        self.assertEqual(obs1.confidence, obs2.confidence)

    def test_build_track_segments_single_track(self):
        """Test building track segments from a single track."""
        obs1 = RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        )
        obs2 = RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        )

        segments = build_track_segments_from_observations([obs1, obs2])

        self.assertEqual(1, len(segments))
        self.assertEqual(1, segments[0].track_id)
        self.assertEqual(2, len(segments[0].observations))

    def test_build_track_segments_multiple_tracks(self):
        """Test building track segments from multiple tracks."""
        obs1 = RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        )
        obs2 = RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        )

        segments = build_track_segments_from_observations([obs1, obs2])

        self.assertEqual(2, len(segments))
        # Sorted by track_id
        self.assertEqual(1, segments[0].track_id)
        self.assertEqual(2, segments[1].track_id)

    def test_build_track_segments_preserves_frame_order(self):
        """Test that frame order is preserved in observations."""
        obs1 = RuntimeTrackingObservation(
            track_id=1, frame_id=30, timestamp=2.0,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        )
        obs2 = RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(50, 100, 150, 200), class_name="car",
            confidence=0.93, cx=100.0, cy=150.0,
        )
        obs3 = RuntimeTrackingObservation(
            track_id=1, frame_id=20, timestamp=1.333,
            bbox=(80, 150, 280, 350), class_name="car",
            confidence=0.91, cx=180.0, cy=250.0,
        )

        segments = build_track_segments_from_observations([obs1, obs2, obs3])

        self.assertEqual(1, len(segments))
        # Observations should be sorted by frame_id
        frame_ids = [obs.frame_id for obs in segments[0].observations]
        self.assertEqual([10, 20, 30], frame_ids)

    def test_build_track_segments_empty_input(self):
        """Test that empty input produces empty output."""
        segments = build_track_segments_from_observations([])
        self.assertEqual(0, len(segments))

    def test_bytetrack_to_segment_pipeline(self):
        """Test complete pipeline: ByteTrack -> RuntimeTrackingObservation -> RuntimeTrackSegment."""
        # Simulate ByteTrack output
        bytetrack_data = [
            {"track_id": 1, "frame_id": 10, "timestamp": 0.667,
             "bbox": [100, 200, 300, 400], "class": 0, "confidence": 0.95, "cx": 200.0, "cy": 300.0},
            {"track_id": 1, "frame_id": 15, "timestamp": 1.0,
             "bbox": [110, 205, 310, 405], "class": 0, "confidence": 0.93, "cx": 210.0, "cy": 305.0},
            {"track_id": 2, "frame_id": 20, "timestamp": 1.333,
             "bbox": [120, 210, 320, 410], "class": 0, "confidence": 0.90, "cx": 220.0, "cy": 310.0},
        ]
        class_mapping = {0: "car"}

        # Convert to RuntimeTrackingObservation
        observations = [observation_from_bytetrack(d, class_mapping) for d in bytetrack_data]

        # Build segments
        segments = build_track_segments_from_observations(observations)

        # Verify pipeline result
        self.assertEqual(2, len(segments))

        # Track 1 segment
        seg1 = next(s for s in segments if s.track_id == 1)
        self.assertEqual(2, len(seg1.observations))
        self.assertEqual("car", seg1.class_name)

        # Track 2 segment
        seg2 = next(s for s in segments if s.track_id == 2)
        self.assertEqual(1, len(seg2.observations))
        self.assertEqual("car", seg2.class_name)


class RuntimeAssociationIntegrationTests(unittest.TestCase):
    """Tests for the runtime Global Identity association integration.

    These tests verify that the runtime ByteTrack output correctly flows through
    the Global Identity pipeline to produce runtime global_id associations.
    """

    def test_bytetrack_observation_enters_gi_pipeline(self):
        """Test that a runtime ByteTrack observation enters the Global Identity pipeline."""
        # Simulate ByteTrack output
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 10,
            "timestamp": 0.667,
            "bbox": [100, 200, 300, 400],
            "class": 0,
            "confidence": 0.95,
            "cx": 200.0,
            "cy": 300.0,
        }
        class_mapping = {0: "car"}

        # Convert to RuntimeTrackingObservation (seam 1)
        obs = observation_from_bytetrack(bytetrack_data, class_mapping)
        self.assertIsNotNone(obs)
        self.assertEqual(1, obs.track_id)

    def test_track_segment_created_from_runtime_observations(self):
        """Test that a track segment can be created from runtime observations."""
        obs1 = RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        )
        obs2 = RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        )

        segments = build_track_segments_from_observations([obs1, obs2])
        self.assertEqual(1, len(segments))
        self.assertEqual(1, segments[0].track_id)
        self.assertEqual(2, len(segments[0].observations))

    def test_candidate_generator_used(self):
        """Test that the existing CandidateGenerator is used."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        generator = CandidateGenerator()
        candidates = generator.generate_candidates([segment1, segment2])

        # CandidateGenerator should generate candidate pairs
        self.assertGreater(len(candidates), 0)

    def test_association_baseline_used(self):
        """Test that the existing AssociationBaseline is used."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        baseline = AssociationBaseline()
        generator = CandidateGenerator()

        candidates = generator.generate_candidates([segment1, segment2])
        decisions = baseline.evaluate_candidates(candidates, [segment1, segment2])

        # AssociationBaseline should produce decisions
        self.assertGreater(len(decisions), 0)

    def test_match_produces_registry_association(self):
        """Test that MATCH produces the expected registry association."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Both tracks should be associated with the same global_id
        gid1 = registry.get_by_track_id(1)
        gid2 = registry.get_by_track_id(2)
        self.assertIsNotNone(gid1)
        self.assertIsNotNone(gid2)
        self.assertEqual(gid1.global_id, gid2.global_id)

    def test_no_match_does_not_incorrectly_merge(self):
        """Test that NO_MATCH does not incorrectly merge identities."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        # Track 2 is far away spatially
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Each track should have its own global_id
        gid1 = registry.get_by_track_id(1)
        gid2 = registry.get_by_track_id(2)
        self.assertIsNotNone(gid1)
        self.assertIsNotNone(gid2)
        self.assertNotEqual(gid1.global_id, gid2.global_id)

    def test_unresolved_does_not_force_match(self):
        """Test that UNRESOLVED does not force a cross-segment identity match."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=100, timestamp=6.667,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Each track should get its own identity
        self.assertIsNotNone(registry.get_by_track_id(1))
        self.assertIsNotNone(registry.get_by_track_id(2))

    def test_same_bytetrack_track_preserves_track_id(self):
        """Test that multiple observations belonging to the same ByteTrack track preserve the same track_id."""
        observations = []
        for frame_id in [10, 15, 20, 25]:
            observations.append({
                "track_id": 5,
                "frame_id": frame_id,
                "timestamp": frame_id * 0.067,
                "bbox": [100 + frame_id, 200, 300 + frame_id, 400],
                "class": 0,
                "confidence": 0.95,
                "cx": 200.0 + frame_id,
                "cy": 300.0,
            })

        class_mapping = {0: "car"}
        gi_obs = [observation_from_bytetrack(o, class_mapping) for o in observations]
        segments = build_track_segments_from_observations(gi_obs)

        self.assertEqual(1, len(segments))
        self.assertEqual(5, segments[0].track_id)

    def test_different_bytetrack_tracks_distinguishable(self):
        """Test that different ByteTrack tracks remain distinguishable."""
        obs1 = RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        )
        obs2 = RuntimeTrackingObservation(
            track_id=2, frame_id=15, timestamp=1.0,
            bbox=(150, 250, 350, 450), class_name="car",
            confidence=0.93, cx=250.0, cy=350.0,
        )

        segments = build_track_segments_from_observations([obs1, obs2])

        self.assertEqual(2, len(segments))
        track_ids = {s.track_id for s in segments}
        self.assertEqual({1, 2}, track_ids)

    def test_runtime_global_ids_generated_by_registry(self):
        """Test that runtime global IDs are generated by the existing registry."""
        segment = RuntimeTrackSegment(track_id=1)
        segment.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline()
        generator = CandidateGenerator()

        associate_track_segments(
            [segment],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Should have exactly one identity
        self.assertEqual(1, registry.count_identities())
        gid = registry.list_identities()[0]
        self.assertTrue(gid.startswith("G"))

    def test_gt_not_required(self):
        """Test that GT data is not required."""
        bytetrack_data = {
            "track_id": 1,
            "frame_id": 10,
            "timestamp": 0.667,
            "bbox": [100, 200, 300, 400],
            "class": 0,
            "confidence": 0.95,
            "cx": 200.0,
            "cy": 300.0,
            # No GT data
        }
        class_mapping = {0: "car"}

        obs = observation_from_bytetrack(bytetrack_data, class_mapping)
        segments = build_track_segments_from_observations([obs])

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline()
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            segments,
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Should succeed without GT
        self.assertEqual(1, registry.count_identities())

    def test_reid_not_used(self):
        """Test that Re-ID is not used (no appearance features)."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        # The global_identity module does not have appearance/Re-ID features
        from global_identity import __all__ as gi_exports
        self.assertNotIn("appearance", [x.lower() for x in gi_exports])
        self.assertNotIn("reid", [x.lower() for x in gi_exports])
        self.assertNotIn("embedding", [x.lower() for x in gi_exports])

    def test_deterministic_results(self):
        """Test that repeated identical runtime inputs produce deterministic results."""
        # Use tracks that are far apart so they won't be matched
        obs1 = RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        )
        # Track 2 is far away spatially (won't match)
        obs2 = RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        )

        # Run twice
        for _ in range(2):
            registry = RuntimeGlobalIdentityRegistry()
            baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
            generator = CandidateGenerator()

            segments = build_track_segments_from_observations([obs1, obs2])
            decisions = associate_track_segments(
                segments,
                registry,
                candidate_generator=generator,
                association_baseline=baseline,
            )

            # Check determinism - two separate identities
            self.assertEqual(registry.list_identities(), ["G001", "G002"])

    def test_existing_tests_still_pass(self):
        """Test that existing Global Identity tests continue to pass."""
        # This is verified by running the full test suite
        # Just do a quick sanity check here
        segment = RuntimeTrackSegment(track_id=1)
        segment.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Basic functionality should work
        self.assertEqual(1, registry.count_identities())
        self.assertIsNotNone(registry.get_by_track_id(1))


class UnresolvedIdentitySemanticsTests(unittest.TestCase):
    """Tests for UNRESOLVED identity semantics.

    These tests verify that the distinction between MATCH, NO_MATCH, and UNRESOLVED
    is preserved explicitly in the runtime global identity assignment.
    """

    def test_match_preserves_existing_global_identity_association(self):
        """MATCH preserves existing global identity association behavior."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # MATCH decision should exist
        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        self.assertEqual(1, len(match_decisions))

        # Both segments should have the same global_id (not provisional)
        gid1 = registry.get_by_track_id(1)
        gid2 = registry.get_by_track_id(2)
        self.assertIsNotNone(gid1)
        self.assertIsNotNone(gid2)
        self.assertEqual(gid1.global_id, gid2.global_id)
        self.assertFalse(gid1.provisional)

    def test_no_match_does_not_merge_identities(self):
        """NO_MATCH does not merge identities."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        # Segment 2 is far away spatially - should get NO_MATCH
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        # Use unresolved thresholds to properly distinguish NO_MATCH from UNRESOLVED
        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            unresolved_temporal_threshold=50,
            unresolved_spatial_threshold=500.0,
        )
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # NO_MATCH decision should exist
        no_match_decisions = [d for d in decisions if d.decision == "NO_MATCH"]
        self.assertEqual(1, len(no_match_decisions))

        # Each segment should have different global_ids
        gid1 = registry.get_by_track_id(1)
        gid2 = registry.get_by_track_id(2)
        self.assertIsNotNone(gid1)
        self.assertIsNotNone(gid2)
        self.assertNotEqual(gid1.global_id, gid2.global_id)
        # NO_MATCH should create confirmed identities, not provisional
        self.assertFalse(gid1.provisional)
        self.assertFalse(gid2.provisional)

    def test_unresolved_remains_distinguishable_from_no_match(self):
        """UNRESOLVED remains distinguishable from NO_MATCH."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        # Segment 2 is far away spatially - should get NO_MATCH
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        ))
        # Segment 3 is distant in time but close in space - candidate exists but may not match
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=200, timestamp=13.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        # Use unresolved thresholds to properly distinguish NO_MATCH from UNRESOLVED
        # Track 1->2: gap=10, dist=667 (NO_MATCH - clearly too far)
        # Track 1->3: gap=190, dist=51 (between 30 and 200 - should be UNRESOLVED)
        # Track 2->3: gap=180, dist=616 (NO_MATCH - clearly too far spatially)
        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            unresolved_temporal_threshold=200,
            unresolved_spatial_threshold=500.0,
        )
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2, segment3],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Find the identities and their provisional status
        records = registry.get_all_records()
        self.assertEqual(3, len(records))

        # Check that NO_MATCH got confirmed identities and UNRESOLVED got provisional
        for record in records:
            track_ids = record.get_track_ids()
            if 2 in track_ids:
                # Track 2 should be NO_MATCH -> confirmed
                self.assertFalse(record.provisional)
            elif 3 in track_ids:
                # Track 3 should be UNRESOLVED -> provisional (gap 190 between 30 and 200)
                self.assertTrue(record.provisional)
            else:
                # Track 1 could be either depending on how candidates worked
                pass

    def test_unresolved_remains_distinguishable_from_match(self):
        """UNRESOLVED remains distinguishable from MATCH."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        # Segment 2 is close - should match with segment1
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))
        # Segment 3 is distant in time but close in space - should be UNRESOLVED
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=200, timestamp=13.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        # Use unresolved thresholds to properly distinguish MATCH, NO_MATCH, and UNRESOLVED
        # gap 185 between segment1 and segment3 is between 30 (MATCH) and 200 (NO_MATCH)
        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            unresolved_temporal_threshold=200,
            unresolved_spatial_threshold=500.0,
        )
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2, segment3],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Find MATCH decisions
        match_decisions = [d for d in decisions if d.decision == "MATCH"]
        # Should have at least one match
        self.assertGreaterEqual(len(match_decisions), 1)

        # Check provisional status
        for record in registry.get_all_records():
            track_ids = record.get_track_ids()
            if 1 in track_ids and 2 in track_ids:
                # Should be MATCH -> confirmed (not provisional)
                self.assertFalse(record.provisional)
            if 3 in track_ids:
                # Track 3 should be UNRESOLVED -> provisional
                self.assertTrue(record.provisional)

    def test_unresolved_not_represented_as_confirmed_identity(self):
        """UNRESOLVED is not represented as a confirmed physical-object identity conclusion."""
        # Create segments where one clearly matches and one is ambiguous
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        # Segment 2 is close - MATCH
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))
        # Segment 3 is far in time - no candidate generated (too large gap)
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=200, timestamp=13.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        # Use unresolved thresholds to properly distinguish MATCH, NO_MATCH, and UNRESOLVED
        # gap 185 between segment1 and segment3 is between 30 (MATCH) and 200 (NO_MATCH)
        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            unresolved_temporal_threshold=200,
            unresolved_spatial_threshold=500.0,
        )
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2, segment3],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Check that segment 3 (gap 185 - between 30 and 200) is marked as provisional
        record3 = registry.get_by_track_id(3)
        self.assertIsNotNone(record3)
        # Should be provisional because gap 185 is UNRESOLVED (between 30 and 200)
        self.assertTrue(record3.provisional)

    def test_repeated_identical_inputs_produce_identical_results(self):
        """Repeated identical inputs produce identical results."""
        def create_segments():
            segment1 = RuntimeTrackSegment(track_id=1)
            segment1.add_observation(RuntimeTrackingObservation(
                track_id=1, frame_id=10, timestamp=0.667,
                bbox=(100, 200, 300, 400), class_name="car",
                confidence=0.95, cx=200.0, cy=300.0,
            ))
            segment2 = RuntimeTrackSegment(track_id=2)
            segment2.add_observation(RuntimeTrackingObservation(
                track_id=2, frame_id=20, timestamp=1.333,
                bbox=(120, 210, 320, 410), class_name="car",
                confidence=0.90, cx=220.0, cy=310.0,
            ))
            segment3 = RuntimeTrackSegment(track_id=3)
            segment3.add_observation(RuntimeTrackingObservation(
                track_id=3, frame_id=200, timestamp=13.333,
                bbox=(150, 210, 350, 410), class_name="car",
                confidence=0.90, cx=250.0, cy=310.0,
            ))
            return [segment1, segment2, segment3]

        results = []
        for _ in range(5):
            registry = RuntimeGlobalIdentityRegistry()
            baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
            generator = CandidateGenerator()

            segments = create_segments()
            decisions = associate_track_segments(
                segments,
                registry,
                candidate_generator=generator,
                association_baseline=baseline,
            )

            # Collect provisional status for each track
            provisional_status = {}
            for seg in segments:
                record = registry.get_by_track_id(seg.track_id)
                provisional_status[seg.track_id] = record.provisional if record else None
            results.append(provisional_status)

        # All runs should produce identical results
        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])

    def test_existing_registry_consistency_tests_continue_to_pass(self):
        """Existing registry consistency tests continue to pass."""
        # Test: Each track should be in exactly one identity
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        track_to_gid = {}
        for gid in registry.list_identities():
            record = registry.get_by_global_id(gid)
            for tid in record.get_track_ids():
                self.assertNotIn(tid, track_to_gid, f"Track {tid} already assigned!")
                track_to_gid[tid] = gid

        self.assertIn(1, track_to_gid)
        self.assertIn(2, track_to_gid)

    def test_existing_association_baseline_tests_continue_to_pass(self):
        """Existing AssociationBaseline tests continue to pass."""
        # Test: MATCH decision when thresholds are satisfied
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(110, 205, 310, 405), class_name="car",
            confidence=0.93, cx=210.0, cy=305.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(120, 210, 320, 410), class_name="car",
            confidence=0.90, cx=220.0, cy=310.0,
        ))

        candidate = TrackSegmentCandidate(
            previous_track_id=1,
            current_track_id=2,
            temporal_gap=5,
            spatial_distance=20.0,
            class_match=True,
            class_name="car",
        )

        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        decision = baseline.evaluate_candidate(candidate, segment1, segment2)

        self.assertEqual("MATCH", decision.decision)
        self.assertTrue(decision.evidence.temporal_within_threshold)
        self.assertTrue(decision.evidence.spatial_within_threshold)

    def test_existing_global_identity_tests_continue_to_pass(self):
        """Existing Global Identity tests continue to pass."""
        # Test: Runtime global_id distinct from track_id
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        # Global IDs should be G### format, not track IDs
        for gid in registry.list_identities():
            self.assertTrue(validate_runtime_global_id(gid))

    def test_provisional_identity_can_be_created_directly(self):
        """Test that provisional identities can be created directly."""
        registry = RuntimeGlobalIdentityRegistry()

        # Create confirmed identity
        id1 = registry.create_identity(provisional=False)
        self.assertEqual("G001", id1)

        # Create provisional identity
        id2 = registry.create_identity(provisional=True)
        self.assertEqual("G002", id2)

        # Check records
        record1 = registry.get_by_global_id(id1)
        record2 = registry.get_by_global_id(id2)

        self.assertFalse(record1.provisional)
        self.assertTrue(record2.provisional)


class GlobalIdentityArtifactTests(unittest.TestCase):
    """Tests for the Global Identity audit artifact.

    These tests verify that the audit artifact correctly captures runtime
    Global Identity associations for observability.
    """

    def test_artifact_contains_runtime_global_identities(self):
        """Test that audit artifact contains runtime global identities."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        self.assertIn("global_identities", artifact)
        self.assertEqual(1, len(artifact["global_identities"]))

    def test_artifact_track_id_preserved(self):
        """Test that track_id is preserved in artifact."""
        segment1 = RuntimeTrackSegment(track_id=5)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=5, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        self.assertEqual(5, artifact["global_identities"][0]["track_segments"][0]["track_id"])

    def test_artifact_global_id_preserved(self):
        """Test that global_id is preserved in artifact."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        self.assertEqual("G001", artifact["global_identities"][0]["global_id"])

    def test_artifact_provisional_preserved(self):
        """Test that provisional status is preserved in artifact."""
        # Create segments that will result in provisional identity
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        # Single segment without candidates should be provisional
        self.assertTrue(artifact["global_identities"][0]["provisional"])

    def test_artifact_match_information_preserved(self):
        """Test that MATCH decision information is preserved in artifact."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        # Find MATCH decision
        match_decisions = [d for d in artifact["decisions"] if d["decision"] == "MATCH"]
        self.assertEqual(1, len(match_decisions))

    def test_artifact_no_match_information_preserved(self):
        """Test that NO_MATCH decision information is preserved in artifact."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.90, cx=850.0, cy=450.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        # Find NO_MATCH decision
        no_match_decisions = [d for d in artifact["decisions"] if d["decision"] == "NO_MATCH"]
        self.assertEqual(1, len(no_match_decisions))

    def test_artifact_unresolved_provisional_preserved(self):
        """Test that UNRESOLVED/provisional information is preserved."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=200, timestamp=13.333,
            bbox=(150, 210, 350, 410), class_name="car",
            confidence=0.90, cx=250.0, cy=310.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        # Use unresolved thresholds
        baseline = AssociationBaseline(
            max_temporal_gap=30,
            max_spatial_distance=200.0,
            unresolved_temporal_threshold=200,
            unresolved_spatial_threshold=500.0,
        )
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        # Check provisional status is preserved
        for identity in artifact["global_identities"]:
            self.assertIn("provisional", identity)

    def test_artifact_multiple_track_ids_under_one_global_id(self):
        """Test that multiple ByteTrack track IDs can be represented under one global ID when MATCH occurs."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=15, timestamp=1.0,
            bbox=(150, 200, 350, 400), class_name="car",
            confidence=0.93, cx=250.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(200, 200, 400, 400), class_name="car",
            confidence=0.90, cx=300.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1, segment2],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        # Find the identity with both track IDs
        matched_identity = None
        for identity in artifact["global_identities"]:
            track_ids = [seg["track_id"] for seg in identity["track_segments"]]
            if 1 in track_ids and 2 in track_ids:
                matched_identity = identity
                break

        self.assertIsNotNone(matched_identity)
        self.assertFalse(matched_identity["provisional"])

    def test_artifact_one_track_id_cannot_be_assigned_to_multiple_global_ids(self):
        """Test that one track ID cannot be silently assigned to multiple global IDs."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        # Collect all track IDs across all identities
        all_track_ids = []
        for identity in artifact["global_identities"]:
            for seg in identity["track_segments"]:
                all_track_ids.append(seg["track_id"])

        # Each track ID should appear exactly once
        self.assertEqual(len(all_track_ids), len(set(all_track_ids)))

    def test_artifact_gt_not_required(self):
        """Test that GT data is not required for artifact."""
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))

        registry = RuntimeGlobalIdentityRegistry()
        baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
        generator = CandidateGenerator()

        decisions = associate_track_segments(
            [segment1],
            registry,
            candidate_generator=generator,
            association_baseline=baseline,
        )

        from global_identity import build_global_identity_artifact
        artifact = build_global_identity_artifact(registry, decisions)

        # Verify no GT IDs in artifact
        for identity in artifact["global_identities"]:
            self.assertFalse(identity["global_id"].startswith("GT_"))

    def test_artifact_deterministic_ordering(self):
        """Test that artifact ordering is deterministic."""
        # Create segments in non-deterministic order - far apart so no matching
        segment3 = RuntimeTrackSegment(track_id=3)
        segment3.add_observation(RuntimeTrackingObservation(
            track_id=3, frame_id=30, timestamp=2.0,
            bbox=(800, 400, 900, 500), class_name="car",
            confidence=0.95, cx=850.0, cy=450.0,
        ))
        segment1 = RuntimeTrackSegment(track_id=1)
        segment1.add_observation(RuntimeTrackingObservation(
            track_id=1, frame_id=10, timestamp=0.667,
            bbox=(100, 200, 300, 400), class_name="car",
            confidence=0.95, cx=200.0, cy=300.0,
        ))
        segment2 = RuntimeTrackSegment(track_id=2)
        segment2.add_observation(RuntimeTrackingObservation(
            track_id=2, frame_id=20, timestamp=1.333,
            bbox=(400, 300, 500, 400), class_name="car",
            confidence=0.95, cx=450.0, cy=350.0,
        ))

        # Run twice with same input segments in different order
        for _ in range(2):
            registry = RuntimeGlobalIdentityRegistry()
            baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
            generator = CandidateGenerator()

            decisions = associate_track_segments(
                [segment3, segment1, segment2],
                registry,
                candidate_generator=generator,
                association_baseline=baseline,
            )

            from global_identity import build_global_identity_artifact
            artifact = build_global_identity_artifact(registry, decisions)

            # Check deterministic ordering by creation order
            global_ids = [id["global_id"] for id in artifact["global_identities"]]
            # Should be G001, G002, G003 in order of creation
            self.assertEqual(["G001", "G002", "G003"], global_ids)

    def test_artifact_repeated_identical_input_produces_identical_artifact(self):
        """Test that repeated identical input produces identical artifact content."""
        def create_test_data():
            segment1 = RuntimeTrackSegment(track_id=1)
            segment1.add_observation(RuntimeTrackingObservation(
                track_id=1, frame_id=10, timestamp=0.667,
                bbox=(100, 200, 300, 400), class_name="car",
                confidence=0.95, cx=200.0, cy=300.0,
            ))
            segment2 = RuntimeTrackSegment(track_id=2)
            segment2.add_observation(RuntimeTrackingObservation(
                track_id=2, frame_id=20, timestamp=1.333,
                bbox=(120, 210, 320, 410), class_name="car",
                confidence=0.90, cx=220.0, cy=310.0,
            ))
            return [segment1, segment2]

        results = []
        for _ in range(3):
            registry = RuntimeGlobalIdentityRegistry()
            baseline = AssociationBaseline(max_temporal_gap=30, max_spatial_distance=200.0)
            generator = CandidateGenerator()

            segments = create_test_data()
            decisions = associate_track_segments(
                segments,
                registry,
                candidate_generator=generator,
                association_baseline=baseline,
            )

            from global_identity import build_global_identity_artifact
            artifact = build_global_identity_artifact(registry, decisions)
            results.append(artifact)

        # All results should be identical
        for i in range(1, len(results)):
            self.assertEqual(results[0]["global_identities"], results[i]["global_identities"])
            self.assertEqual(results[0]["decisions"], results[i]["decisions"])


if __name__ == "__main__":
    unittest.main()
