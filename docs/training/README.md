# Training Configuration Records

This directory contains sanitized configuration records for two YOLOv8m
training experiments.

## Experiments

| Experiment | Device | Dataset | Configuration |
|---|---|---|---|
| train-13 | CPU | My-First-Project-4 | `train-13-args.yaml` |
| train-16 | GPU 0 | My-First-Project-4 | `train-16-args.yaml` |

## Configuration provenance

The YAML files are derived from the original Ultralytics training
configuration files:

- `runs/detect/train-13/args.yaml`
- `runs/detect/train-16/args.yaml`

Only machine-specific absolute paths were replaced with repository-relative
paths. Other recorded parameters were retained.

## Important differences

The two experiments are not identical:

- train-13 used CPU; train-16 used GPU 0.
- train-16 includes additional parameters: `dlog`, `dgrad`, and `dlam`.
- Both configurations specify YOLOv8m, 100 epochs, batch size 8,
  image size 640, and learning rate 0.0005.

Therefore, their results should not be interpreted as a controlled
CPU-versus-GPU comparison.

## Results

The corresponding training logs are:

- `../../runs/detect/train-13/results.csv`
- `../../runs/detect/train-16/results.csv`

These paths describe their locations in the repository. The configuration
records are historical experiment documentation; they are not guaranteed
to be directly executable without resolving dataset, model, and runtime
dependencies.

## Privacy

Machine-specific absolute paths have been removed. No API keys, access
tokens, or passwords are intentionally included in these records.