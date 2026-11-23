# 3. Numerical Baseline Findings

This section presents the full-subset numerical metrics at the evaluated operating point. All findings in this section are numerical evidence (evidence level LEVEL_A), computed over the complete evaluated valid and test subsets. They are distinct from the visual evidence confined to the 12 inspected cases.

At the evaluated operating point, recall is substantially higher than precision in both evaluated splits:

- Valid: recall 0.862152, precision 0.223023.
- Test: recall 0.873055, precision 0.222698.

False positives are numerous relative to true positives in both evaluated splits:

- Valid: total true positives 2877, total false positives 10023.
- Test: total true positives 1403, total false positives 4897.

False negatives occur across the evaluated classes in both splits:

- Valid: total false negatives 460.
- Test: total false negatives 204.

Valid and test aggregate performance are close on all four overall metrics:

- Valid: mAP@0.5 0.680575, mAP@0.5:0.95 0.319892, precision 0.223023, recall 0.862152.
- Test: mAP@0.5 0.676974, mAP@0.5:0.95 0.319613, precision 0.222698, recall 0.873055.
- Valid minus test differences: mAP@0.5 0.003601, mAP@0.5:0.95 0.000279, precision 0.000325, recall -0.010903.

The valid/test difference cannot be established as statistically significant. No statistical significance test was performed, and the differences are small in absolute terms. No generalization failure can be concluded from these differences.

The gap between average precision at IoU 0.50 and average precision over IoU 0.50-0.95 is substantial for every evaluated class in both splits:

- Bus: AP@0.5 0.857143 (valid) / 0.800000 (test); AP@0.5:0.95 0.397619 (valid) / 0.39 (test).
- Car: AP@0.5 0.895222 (valid) / 0.894281 (test); AP@0.5:0.95 0.432775 (valid) / 0.422704 (test).
- Motorcycle: AP@0.5 0.846828 (valid) / 0.865591 (test); AP@0.5:0.95 0.399742 (valid) / 0.391613 (test).
- Truck: AP@0.5 0.803681 (valid) / 0.825000 (test); AP@0.5:0.95 0.369325 (valid) / 0.39375 (test).

This gap is partially consistent with localization weakness, but the numerical evidence cannot establish that localization is the sole or primary weakness, nor that it applies to any specific inspected case.

The evaluated validation subset contains 43 images with 3337 ground-truth objects and 12900 predictions. The evaluated test subset contains 21 images with 1607 ground-truth objects and 6300 predictions.

The person class is a documented limitation of the evaluated scope. The person class has no ground truth in either the validation or the test subset (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.

Model architecture, training procedure, hardware, and hyperparameters are not established by the source artifacts and are therefore not reported.