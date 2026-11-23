# 6. Visual Evidence

This section presents the visual inspection records and their evidence-level constraints. All findings in this section are visual evidence (evidence level LEVEL_C). They are distinct from the full-subset numerical evidence (evidence level LEVEL_A) described in Section 3.

VE-01

Single-image visual inspection records exist for 12 cases (VC-01 through VC-12); one from the validation split (VC-09) and eleven from the test split.

VE-02

No new visual observations were created during evidence integration; the categories are those already recorded in the source artifacts.

VE-03

The BORDERLINE_IOU_MATCH category is the only visual category with full support (SUPPORTED); all other categories are PARTIALLY_SUPPORTED or NOT_DIRECTLY_SUPPORTED.

VE-04

The 12-case sample is a deterministic error-analysis sample selected from matching evidence, not a statistically representative random sample of the dataset.

VE-05

Visual findings are observations made in the inspected cases and must not be described as what the dataset as a whole contains unless independently supported by full-subset numerical evidence.

The visual evidence consists of 12 inspected cases. Their split composition is exactly: one case from the validation split (VC-09) and eleven cases from the test split. No dataset-wide prevalence of any visual error category is claimed.

The 12-case sample is deterministic and is an error-analysis sample, not a statistically representative random sample of the dataset. Visual findings apply to the inspected cases only unless independently supported by full-subset numerical evidence.

Support-status boundary: BORDERLINE_IOU_MATCH is the only category with full SUPPORT. All other categories remain PARTIALLY_SUPPORTED or NOT_DIRECTLY_SUPPORTED. No category was upgraded to SUPPORTED.

Model architecture, training procedure, hardware, and hyperparameters are not established by the source artifacts and are therefore not reported.