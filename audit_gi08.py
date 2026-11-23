"""GI-08 Independent Audit Script."""
import json
from collections import defaultdict
from evaluation.global_identity_evaluator import (
    evaluate_temporal_consistency,
    evaluate_global_identity_id_switches,
    load_global_identity_registry,
    load_gt_observations,
    evaluate_all_frames,
    build_matched_observations,
)

def main():
    # Run GI-08.9 evaluation
    r = evaluate_temporal_consistency()
    print("=== AUDIT 1: MATCHING CONSISTENCY ===")
    print(f"Total runtime observations: {r['aggregate_summary']['total_runtime_observations']}")
    print(f"Total GT observations: {r['aggregate_summary']['total_gt_observations']}")
    print(f"Matched observations: {r['aggregate_summary']['total_matched_observations']}")
    print(f"Unmatched runtime observations: {r['aggregate_summary']['total_unmatched_runtime_observations']}")

    total_runtime = r['aggregate_summary']['total_runtime_observations']
    total_matched = r['aggregate_summary']['total_matched_observations']
    total_unmatched = r['aggregate_summary']['total_unmatched_runtime_observations']
    print(f"\nAccounting check: {total_matched} + {total_unmatched} = {total_matched + total_unmatched} (should equal {total_runtime})")

    # ID Preserved Score
    print("\n=== AUDIT 2: ID PRESERVED SCORE ===")
    id_preserved = r['id_preserved_details']
    print(f"ID Preserved Score: {r['aggregate_summary']['id_preserved_score']}")
    print(f"Total matched observations: {id_preserved['total_matched_observations']}")
    print(f"Consistent observations: {id_preserved['total_consistent_observations']}")

    # Fragmentation
    print("\n=== AUDIT 3: FRAGMENTATION ===")
    frag = r['fragmentation_summary']
    print(f"Fragmentation count: {frag['fragmentation_count']}")
    print(f"Total GT identities: {frag['total_gt_identities']}")
    print(f"Fragmented GT identities: {frag['fragmented_gt_identities']}")

    # Merge
    print("\n=== AUDIT 4: MERGE ===")
    merge = r['merge_summary']
    print(f"Merge count: {merge['merge_count']}")
    print(f"Merged runtime identities: {merge['merged_runtime_identities']}")
    print(f"Total runtime identities: {merge['total_runtime_identities']}")

    # Provisional identities
    print("\n=== AUDIT 5: PROVISIONAL IDENTITIES ===")
    prov = r['provisional_summary']
    gi_registry = load_global_identity_registry("outputs/global_identity.json")
    print(f"Total runtime global IDs: {len(gi_registry)}")
    print(f"Confirmed global IDs: {len(prov['confirmed_global_ids'])}")
    print(f"Provisional global IDs: {len(prov['provisional_global_ids'])}")
    print(f"Confirmed IDs: {prov['confirmed_global_ids']}")
    print(f"Provisional IDs: {prov['provisional_global_ids']}")

    # Per-class
    print("\n=== AUDIT 6: PER-CLASS CONSISTENCY ===")
    per_class = r['per_class_summary']
    for cls in ['car', 'motorcycle', 'bus', 'truck']:
        print(f"{cls}: matched={per_class[cls]['total_matched_observations']}, score={per_class[cls]['id_preserved_score']}")

    # GI-08.10 ID switches
    print("\n=== AUDIT 7: ID-SWITCH CONSISTENCY ===")
    switch_r = evaluate_global_identity_id_switches()
    agg = switch_r['aggregate_summary']
    print(f"GT identities analyzed: {agg['total_gt_identities_analyzed']}")
    print(f"Candidate transitions: {agg['candidate_transitions']}")
    print(f"Confirmed GI ID switches: {agg['confirmed_gi_id_switches']}")
    print(f"Upstream gap/unresolved: {agg['upstream_gap_or_unresolved']}")
    print(f"Insufficient GT evidence: {agg['insufficient_gt_evidence']}")

if __name__ == "__main__":
    main()
