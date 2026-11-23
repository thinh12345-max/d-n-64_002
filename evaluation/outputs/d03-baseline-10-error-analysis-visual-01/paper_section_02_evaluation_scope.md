# 2. Evaluation Scope

This section defines the evaluated splits, their sample sizes, and the deterministic 12-case visual error-analysis sample.

Two subsets were evaluated, and the distinction between them is preserved throughout this document:

- The validation subset contains 43 images with 3,337 ground-truth objects and 12,900 predictions.
- The test subset contains 21 images with 1,607 ground-truth objects and 6,300 predictions.

Full-subset numerical metrics were computed over both subsets. These metrics constitute numerical evidence (evidence level LEVEL_A). They concern the complete evaluated subsets and are distinct from the visual evidence described below.

The visual error-analysis sample consists of 12 inspected cases, designated VC-01 through VC-12. Their split composition is: one case (VC-09) originates from the validation split and eleven cases originate from the test split. The 12 cases constitute visual evidence (evidence level LEVEL_C) and are confined to those cases; they do not establish what the dataset as a whole contains.

The 12 selected images were matched using a class-aware, greedy, confidence-ranked, one-to-one matching procedure with an IoU threshold of 0.50 and no non-maximum suppression at evaluation time. Aggregate matching totals for the 12 selected images are 781 true positives, 2,819 false positives, and 182 false negatives. Duplicate detections recorded in the visual cases are an artefact of the greedy one-to-one matching rule, not a measured property of the detector.

The 12-case sample is a deterministic error-analysis sample selected from matching evidence. It is not a statistically representative random sample of the dataset, and no statistical significance may be inferred from it. No generalization failure can be concluded from individual case differences.

The person class is a documented limitation of the evaluated scope. The person class has no ground truth in either the validation or the test subset (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.