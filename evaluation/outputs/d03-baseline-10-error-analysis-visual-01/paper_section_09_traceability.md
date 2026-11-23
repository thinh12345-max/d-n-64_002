# 9. Traceability and Source Artifacts

This section documents the provenance of every finding used in this error analysis. The source artifacts are divided into authoritative sources, which carry the primary evidence and interpretation constraints, and supporting sources, which carry the underlying evidence records and audit information. No source artifact other than those listed below was used, and no artifact outside this set is referenced.

## 9.1 Authoritative Sources

The following artifacts are the authoritative sources for this documentation.

- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/research_report.md — Full D-03 report; narrative synthesis of the evidence layers.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/evidence_integration.json — Integrated evidence relationships, support states, machine error evidence, and visual evidence aggregation (LEVEL B and LEVEL C authoritative).
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/scientific_boundary.json — Authoritative interpretation constraints, evidence-level boundary, causal-language boundary, person-class boundary, and sample-scope boundary.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/numerical_baseline_extract.json — Authoritative full valid/test numerical baseline (LEVEL A).

## 9.2 Supporting Sources

The following artifacts are the supporting sources for this documentation.

- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/matching.json — Authoritative 12-image TP/FP/FN machine matching evidence (LEVEL B).
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/visual_inspection.json — Authoritative 12-case visual inspection records (LEVEL C).
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/visual_error_summary.json — Aggregated visual error categories and uncertainty summary.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/evidence_mapping.json — Visual-to-numerical support status for each category.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/final_integrity_validation.json — Integrity audit confirming artifact existence and that no protected file was modified.

## 9.3 Evidence Roles

Each artifact has the evidence role stated in the source record. In particular:

- numerical_baseline_extract.json provides the LEVEL A numerical baseline over the complete evaluated valid/test subsets.
- evidence_integration.json provides the LEVEL B and LEVEL C integrated evidence relationships, support states, and visual evidence aggregation.
- scientific_boundary.json provides the interpretation and scientific boundaries, including the evidence-level, causal-language, person-class, and sample-scope constraints.
- research_report.md provides the full D-03 narrative report.
- matching.json provides the LEVEL B machine matching evidence for the 12 selected images.
- visual_inspection.json provides the LEVEL C visual inspection records for the same 12 cases.
- visual_error_summary.json provides the aggregated visual error categories and uncertainty summary.
- evidence_mapping.json provides the visual-to-numerical support status for each category.
- final_integrity_validation.json provides the artifact integrity audit.

## 9.4 Extraction Note

All numerical values in this documentation are copied verbatim from numerical_baseline_extract.json and evidence_integration.json. No value was computed, derived, or inferred. No source artifact was modified by this extraction.