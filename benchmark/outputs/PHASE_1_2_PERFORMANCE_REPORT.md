# PHASE 1.2 — PERFORMANCE BENCHMARK REPORT

## 1. Objective

Characterize the performance of the current baseline (YOLOv8m + ByteTrack + Entity Association + ROI + Vehicle Counting + JSON Output) to scientifically measure whether the computer-vision pipeline is capable of real-time processing.

## 2. Hardware / Runtime Environment

| Property | Value |
|----------|-------|
| OS | Windows-10-10.0.26200-SP0 |
| Python | 3.10.11 |
| CPU | Intel64 Family 6 Model 151 Stepping 5, GenuineIntel (12 cores) |
| RAM | 16.9 GB |
| PyTorch | 2.13.0+cpu |
| CUDA Available | False |
| GPU | NOT AVAILABLE (CPU-only environment) |

## 3. Software Baseline

| Property | Value |
|----------|-------|
| YOLO Model | YOLOv8m (custom trained) |
| Model Weights | runs/detect/train-16/weights/best.pt |
| Tracker | ByteTrack (bytetrack.yaml) |
| Image Size | 640 |
| Confidence Threshold | 0.30 |
| IoU Threshold | 0.50 |
| Device | CPU (auto → cpu) |
| Frame Size | 1020 × 500 |
| ROI Enabled | True |
| Countable Classes | car, motorcycle, bus, truck, person |

## 4. Benchmark Methodology

| Parameter | Value |
|-----------|-------|
| Warm-up Frames | 30 |
| Benchmark Frames per Run | 500 |
| Number of Runs | 3 |
| Timing Methodology | time.perf_counter() (high-resolution) |
| Measurement Tools | Python stdlib, psutil, custom benchmark script |
| Video Source | public/3.mp4 (1280×720, 15 FPS, 615 frames, 41s) |
| Benchmark Window | Fixed 500 frames (loops video if needed) |

**Warm-up rationale**: 30 frames allows model initialization, memory allocation, and JIT compilation to stabilize. The first frames typically show higher latency due to lazy initialization.

**Note on GPU metrics**: The current environment runs on CPU only (PyTorch CPU build, no CUDA). GPU utilization is NOT AVAILABLE.

## 5. Overall Performance

| Metric | Result |
|--------|--------|
| Input FPS | 15.00 |
| Processing FPS (avg) | **6.72** |
| Total Mean Latency | **146.64 ms** |
| Total Median Latency | **140.50 ms** |
| Total P95 Latency | **188.67 ms** |

**Real-time assessment**: Processing FPS (6.72) < Input FPS (15.00) → **NOT real-time capable** for this video.

## 6. Pipeline Breakdown

Average across 3 runs (500 frames each):

| Stage | Mean (ms) | Median (ms) | P95 (ms) | % of Total |
|-------|-----------|-------------|----------|------------|
| Frame Acquisition | 1.40 | 1.39 | 1.74 | 0.95% |
| YOLO Inference | **115.83** | **110.93** | **149.51** | **79.0%** |
| ByteTrack | 28.96 | 27.73 | 37.26 | 19.7% |
| Entity Association | 0.09 | 0.09 | 0.13 | 0.06% |
| ROI/Counting | 0.01 | 0.01 | 0.01 | 0.01% |
| Visualization/Output | 0.25 | 0.24 | 0.34 | 0.17% |
| **Total** | **146.64** | **140.50** | **188.67** | **100%** |

**Note**: YOLO inference and ByteTrack timing are estimated (80/20 split) since ultralytics runs them together in a single `model.track()` call.

## 7. Resource Usage

| Resource | Average | Maximum |
|----------|---------|---------|
| CPU | 773.3% | 1163.6% |
| RAM | 553.2 MB | 565.9 MB |
| GPU | NOT AVAILABLE | NOT AVAILABLE |

**Note**: CPU % > 100% indicates multi-core utilization (12 cores available). Average ~773% = ~6.4 cores fully utilized.

## 8. Repeatability

| Run | Processing FPS | Mean Latency (ms) | Median Latency (ms) |
|-----|----------------|-------------------|---------------------|
| 1 | 6.67 | 147.74 | 137.86 |
| 2 | 6.76 | 145.58 | 142.01 |
| 3 | 6.72 | 146.60 | 141.62 |
| **Average** | **6.72** | **146.64** | **140.50** |

**Stability**: Results are highly consistent across runs (FPS std dev ≈ 0.045, < 1% variation).

## 9. Bottleneck Analysis

**Primary bottleneck: YOLO Inference (79% of total latency)**

- Mean: 115.83 ms/frame
- Median: 110.93 ms/frame
- P95: 149.51 ms/frame

**Secondary bottleneck: ByteTrack (19.7% of total latency)**

- Mean: 28.96 ms/frame
- Median: 27.73 ms/frame
- P95: 37.26 ms/frame

All other stages (entity association, ROI/counting, visualization) are negligible (< 0.5 ms combined).

The YOLOv8m model running on CPU is the dominant computational bottleneck. The model processes at ~6.7 FPS on this hardware, while the input video runs at 15 FPS.

## 10. Real-Time Assessment

| Question | Answer |
|----------|--------|
| Is processing FPS ≥ input FPS? | **No** (6.72 < 15.00) |
| Is the system capable of processing this video at its input rate? | **No** — processing is ~2.2× slower than input |
| What is the observed latency? | Mean 146.6 ms, Median 140.5 ms, P95 188.7 ms |
| Is the system soft-real-time or strict-real-time? | **Neither** — the system cannot sustain the input frame rate. It operates at ~45% of required throughput. |

**Classification**: The pipeline is **not real-time** for this configuration. It processes at 6.7 FPS on CPU with YOLOv8m at 640×640 resolution.

## 11. Baseline Integrity

| Component | Status |
|-----------|--------|
| YOLOv8m model | ✅ Unchanged |
| Model weights (best.pt) | ✅ Unchanged |
| Configuration (config.yaml) | ✅ Unchanged |
| ByteTrack tracker | ✅ Unchanged |
| ROI definition | ✅ Unchanged |
| Counting logic | ✅ Unchanged |
| Entity association | ✅ Unchanged |
| Frame processing logic | ✅ Unchanged |

The benchmark script is separate from the production pipeline (located in `benchmark/benchmark.py`) and does not modify any baseline components.

## 12. Limitations

1. **Single hardware configuration**: Benchmark run on one CPU-only machine (12-core Intel, 16.9 GB RAM)
2. **Single video**: Tested on public/3.mp4 only (15 FPS, 1280×720, 41s duration)
3. **CPU-only execution**: No GPU/CUDA available — GPU metrics NOT AVAILABLE
4. **YOLO/ByteTrack timing estimation**: Since ultralytics combines inference and tracking in one call, the 80/20 split is an approximation
5. **Fixed benchmark window**: 500 frames (loops video 4.5×) — longer videos might show different thermal/throttling behavior
6. **No thermal monitoring**: CPU frequency scaling under sustained load not measured
7. **Python GIL**: Threading-based resource monitor may have measurement overhead

## 13. Conclusion

The Phase 1.1 baseline (YOLOv8m + ByteTrack on CPU) achieves **6.72 FPS** average processing throughput on the test video (15 FPS input). This represents **45% of real-time performance**.

**Primary bottleneck**: YOLOv8m inference on CPU (79% of latency, ~116 ms/frame mean).

**Implication**: To achieve real-time (≥15 FPS) on this hardware, the pipeline would need ~2.2× speedup. Options include:
- GPU acceleration (CUDA)
- Model quantization/optimization (TensorRT, ONNX Runtime)
- Smaller model variant (YOLOv8s/n)
- Reduced input resolution
- Frame skipping (with accuracy trade-off)

No optimizations have been applied — this report establishes the scientific baseline for Phase 1.2.

---

**Report generated**: 2026-08-16T23:45:21
**Benchmark data**: `benchmark/outputs/performance_summary_20260816_234521.json`
**Run data**: `benchmark/outputs/performance_runs_20260816_234521.csv`