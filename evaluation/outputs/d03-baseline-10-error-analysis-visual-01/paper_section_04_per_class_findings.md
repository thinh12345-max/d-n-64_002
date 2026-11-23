# 4. Per-Class Findings

This section presents per-class results across the evaluated classes. All per-class numerical findings in this section are numerical evidence (evidence level LEVEL_A), computed over the complete evaluated valid and test subsets. They are distinct from the visual case distribution, which is visual evidence (evidence level LEVEL_C) and is confined to the 12 inspected cases.

Bus

- Validation: ground truth 42, predictions 227, true positives 36, false positives 191, false negatives 6, precision 0.15859, recall 0.857143, AP@0.5 0.857143, AP@0.5:0.95 0.397619.
- Test: ground truth 20, predictions 112, true positives 16, false positives 96, false negatives 4, precision 0.142857, recall 0.8, AP@0.5 0.8, AP@0.5:0.95 0.39.

Car

- Validation: ground truth 1193, predictions 5616, true positives 1068, false positives 4548, false negatives 125, precision 0.190171, recall 0.895222, AP@0.5 0.895222, AP@0.5:0.95 0.432775.
- Test: ground truth 577, predictions 2713, true positives 516, false positives 2197, false negatives 61, precision 0.190195, recall 0.894281, AP@0.5 0.894281, AP@0.5:0.95 0.422704.

Motorcycle

- Validation: ground truth 1939, predictions 6342, true positives 1642, false positives 4700, false negatives 297, precision 0.258909, recall 0.846828, AP@0.5 0.846828, AP@0.5:0.95 0.399742.
- Test: ground truth 930, predictions 3096, true positives 805, false positives 2291, false negatives 125, precision 0.260013, recall 0.865591, AP@0.5 0.865591, AP@0.5:0.95 0.391613.

Truck

- Validation: ground truth 163, predictions 715, true positives 131, false positives 584, false negatives 32, precision 0.183217, recall 0.803681, AP@0.5 0.803681, AP@0.5:0.95 0.369325.
- Test: ground truth 80, predictions 379, true positives 66, false positives 313, false negatives 14, precision 0.174142, recall 0.825, AP@0.5 0.825, AP@0.5:0.95 0.39375.

Visual case distribution by class within the 12 inspected cases only (evidence level LEVEL_C): bus 3 (VC-01, VC-02, VC-03); truck 4 (VC-04, VC-05, VC-06, VC-10); motorcycle 4 (VC-07, VC-08, VC-09, VC-12); car 1 (VC-11). This distribution is limited to the 12 inspected cases and is not representative of the full dataset. It must not be described as what the dataset as a whole contains.

The person class is a documented limitation of the evaluated scope. The person class has no ground truth in either the validation or the test subset (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.

Model architecture, training procedure, hardware, and hyperparameters are not established by the source artifacts and are therefore not reported.