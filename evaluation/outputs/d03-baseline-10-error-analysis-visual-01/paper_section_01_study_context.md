# 1. Study Context

This section frames the documentation stage by stating what the present error analysis is and is not. It is a documentation of the existing D-03 baseline evaluation and visual error-analysis evidence. It is not a new experiment, and it introduces no new evidence, no new interpretations, no causal claims, no recommendations, and no hypotheses.

The analysis identified as d03-baseline-10-error-analysis-visual-01 is an extraction-only distillation of paper-ready findings from the frozen D-03 baseline evaluation and the associated visual error analysis. Its stated scope is extraction only: no new evidence was created, no inference was run, no training was performed, the baseline evaluation was not rerun, and no image pixels were inspected.

Three evidence levels are in use and are not interchangeable:

- LEVEL_A: Full-subset numerical metrics over the complete evaluated valid and test subsets.
- LEVEL_B: Machine matching evidence (true positives, false positives, false negatives) for the 12 selected images.
- LEVEL_C: Direct visual inspection observations for the same 12 cases.

A statement supported only by Level C must not be presented as supported by Level A. Numerical evidence and visual evidence are therefore distinguished throughout this document: numerical evidence concerns the full evaluated subsets, while visual evidence is confined to the 12 inspected cases and does not establish dataset-wide prevalence of any observation.

The person class is a documented limitation of the evaluated subsets. The person class has no ground truth in the evaluated validation or test subsets (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.

Model architecture, training procedure, hardware, and hyperparameters are not established by the selected source artifacts and are therefore not reported here.

Every finding documented in this work traces to named source artifacts. The authoritative sources are the full D-03 report, the integrated evidence relationships, the interpretation constraints, and the full valid/test numerical baseline. The supporting sources are the 12-image machine matching evidence, the 12-case visual inspection records, the aggregated visual error categories, the visual-to-numerical support mapping, and the integrity audit. All numerical values are copied verbatim from the source artifacts; no value was computed, derived, or inferred, and no source artifact was modified by this extraction.