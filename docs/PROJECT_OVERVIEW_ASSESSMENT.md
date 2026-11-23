# PROJECT OVERVIEW ASSESSMENT

**Đánh giá độc lập về kiến trúc nghiên cứu**

**Tiêu đề nghiên cứu:** "Ứng dụng YoLov8 để phân tích và theo dõi lưu lượng giao thông theo thời gian thực"

**Ngày đánh giá:** 2026-09-18

---

## 1. Executive Summary

Đánh giá này thực hiện phân tích độc lập về kiến trúc nghiên cứu dựa trên bằng chứng hiện có trong repository. Phạm vi nghiên cứu hiện tại được đánh giá đến **Tầng 5 — Trajectory**.

**Kiến trúc nghiên cứu hiện tại:**

**Video**
→ **Temporal Sampling**
→ **Object Detection**
→ **Multi-Object Tracking**
→ **Global Identity**
→ **Trajectory**

**Điểm mạnh:**
- Kiến trúc 5 tầng được xác định rõ ràng với các ranh giới phân tách hợp lý
- Tầng 1–5 đã được triển khai và đánh giá với bằng chứng đầy đủ
- Có sự nhất quán cao giữa tài liệu đóng (closure documents) và artifacts runtime

**Điểm cần lưu ý:**
- Tầng 1 đang trong quá trình xây dựng và kiểm định
- Tầng 2 có baseline detection với các hạn chế đã được ghi nhận
- Tầng 3 có tracking pipeline đã được đánh giá
- Global Identity có 5 identity tạm thời (provisional), 3 trường hợp merge, và 1,976 observations không khớp
- Tầng 6–9 thuộc định hướng mở rộng của kiến trúc nghiên cứu và chưa thuộc phạm vi đánh giá hiện tại.

**Kết luận sơ bộ:** Dự án đã xây dựng và kiểm định nền tảng nghiên cứu từ dữ liệu đầu vào đến biểu diễn quỹ đạo ở mức độ:

- Tầng 1 (Cơ sở dữ liệu): Đang xây dựng/kiểm định
- Tầng 2 (Nhận diện): Đã có baseline, đang đánh giá
- Tầng 3 (Theo dõi): Đã có pipeline, đã đánh giá
- Tầng 4 (Global Identity): Đã triển khai, đánh giá và đóng
- Tầng 5 (Trajectory): Đã triển khai và kiểm định

---

## 2. Five-Layer Status Matrix

| Tầng | Nội dung | Trạng thái hiện tại |
| ----- | --------------------- | ------------------------------- |
| **1** | Cơ sở dữ liệu | Đang xây dựng/kiểm định |
| **2** | Nhận diện YOLOv8 | Đã có baseline, đang đánh giá |
| **3** | Multi-Object Tracking | Đã có pipeline, đã đánh giá |
| **4** | Global Identity | Đã triển khai, đánh giá và đóng |
| **5** | Trajectory | Đã triển khai và kiểm định |

---

## 3. Layer-by-Layer Assessment

### 3.1 Tầng 1 — Cơ sở dữ liệu (Database)

**Trạng thái:** Đang xây dựng/kiểm định

**Bằng chứng triển khai:**
- Video nguồn: `public/3.mp4` (1280×720, 15 FPS, 615 frames, 41 giây)
- Temporal Sampling: Frame extraction từ video gốc
- Ground Truth: `annotation/data/tracking_ground_truth.json` tồn tại với schema được định nghĩa
- Annotation schemas: `annotation/schema/` chứa các JSON schema cho detection, tracking, và counting
- Frames: `annotation/data/frames/` chứa 107 frames đã được trích xuất

**Bằng chứng đánh giá:**
- [PHASE_1_3A_GROUND_TRUTH_SPEC.md](docs/PHASE_1_3A_GROUND_TRUTH_SPEC.md) xác định specification đầy đủ
- [PHASE_1_3B_ANNOTATION_PROTOCOL.md](docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md) xác định protocol annotation
- Chiến lược temporal block splitting được xác định để tránh data leakage

**Hạn chế:**
- Annotation chưa hoàn thành theo đầy đủ specification
- Chỉ có tracking ground truth, chưa có detection ground truth đầy đủ
- Dataset split (train/val/test) chưa được thực thi rõ ràng

**Đánh giá:** Dữ liệu cơ bản đã được thiết lập với video nguồn và tracking ground truth. Tuy nhiên, annotation đầy đủ theo specification vẫn đang trong quá trình xây dựng.

---

### 3.2 Tầng 2 — Nhận diện (Object Detection)

**Trạng thái:** Đã có baseline, đang đánh giá

**Bằng chứng triển khai:**
- Model: YOLOv8m (custom trained, `runs/detect/train-16/weights/best.pt`)
- Cấu hình: imgsz=640, conf=0.30, IoU=0.50
- Classes: bus (0), car (1), motorcycle (2), truck (3), other (4)
- Config: `config/config.yaml` với centralized parameters

**Bằng chứng đánh giá:**
- Evaluation reports trong `evaluation/outputs/d03-baseline-10-error-analysis-visual-01/`
- Error analysis documents: `paper_section_01` đến `paper_section_10`
- D03 evaluation protocol: `D-03_DETECTION_MODEL_EVALUATION_PROTOCOL.md`
- Performance baseline: 10-frame evaluation với numerical findings

**Hạn chế được ghi nhận:**
- Detection precision/recall không đạt mức cao
- Class-specific limitations (bus: 0.5652 ID Preserved Score, truck: 0 observations matched)
- Small object detection challenges
- Class confusion đã được ghi nhận trong error analysis

**Đánh giá:** Model detection đã được triển khai và đánh giá với baseline metrics. Đây là baseline configuration (conf=0.30), không phải globally optimal. Không có bằng chứng cho claim "optimal" hoặc "best".

---

### 3.3 Tầng 3 — Theo dõi (Multi-Object Tracking)

**Trạng thái:** Đã có pipeline, đã đánh giá

**Bằng chứng triển khai:**
- Tracker: ByteTrack (`bytetrack.yaml`)
- persist: True
- track_id: Runtime identity từ ByteTrack
- Configuration trong `config/config.yaml`

**Bằng chứng đánh giá:**
- Tracking evaluation protocols: `protocol/tracking_evaluation_protocol_D06.*.md`
- Multiple protocol versions: D06.10, D06.27, D06.32 (human decisions)
- IDSW = 0 được ghi nhận theo evaluator convention

**Phân biệt quan trọng:**
- `track_id` là runtime identity từ ByteTrack
- `global_id` là Global Identity được gán sau tracking (Tầng 4)
- IDSW = 0 **không chứng minh** perfect physical identity preservation

**Hạn chế:**
- Không có Re-ID / appearance-based matching
- IDSW = 0 theo convention cụ thể, không phải zero identity errors
- Visibility và occlusion fields không có sẵn runtime

**Đánh giá:** Tracking đã được triển khai với ByteTrack và đánh giá. Cần phân biệt rõ ràng giữa track_id (ByteTrack runtime) và global_id (Global Identity layer).

---

### 3.4 Tầng 4 — Global Identity

**Trạng thái:** Đã triển khai, đánh giá và đóng

**Bằng chứng triển khai:**
- Global Identity registry: `outputs/global_identity.json`
- 15 runtime global IDs
- 10 confirmed, 5 provisional

**Bằng chứng đánh giá:**
- [GI_08_DECISION_RECORD.md](docs/GI_08_DECISION_RECORD.md): Human decisions closed
- [GI_08_EVALUATION_CLOSURE.md](docs/GI_08_EVALUATION_CLOSURE.md): Evidence frozen
- [GI_10_SANITY_AUDIT_CLOSURE.md](docs/GI_10_SANITY_AUDIT_CLOSURE.md): Structural audit closed

**Kết quả định lượng (từ GI-08):**

| Metric | Value |
|--------|-------|
| Total runtime observations | 4,015 |
| GT observations | 3,186 |
| Matched observations | 2,039 |
| Unmatched runtime observations | 1,976 |
| ID Preserved Score | 0.9259 |
| Fragmented GT identities | 0 |
| Merged runtime global IDs | 3 |
| Confirmed GI ID switches (D8) | 0 |

**Confirmed IDs:** G001, G002, G003, G007, G010, G011, G012, G013, G014, G015

**Provisional IDs:** G004, G005, G006, G008, G009

**Giải thích quan trọng:**
- 0.9259 là ID Preserved Score tính **trên matched observations**, **không phải** overall Global Identity accuracy
- 0 confirmed GI ID switches theo D8 criterion, **không có nghĩa** là zero identity errors
- 5 provisional identities có nghĩa là **không đủ bằng chứng association**, **không phải** incorrect identity
- 3 merge cases: G001→GT_017/021/023, G002→GT_018/019/020, G003→GT_026-032

**Multi-track Global IDs:**
- G001: track_ids [9, 23, 30]
- G002: track_ids [12, 14, 16]
- G003: track_ids [48, 58, 75, 90, 91, 95, 97]

**Đánh giá:** Global Identity đã được triển khai, đánh giá, và đóng (closed) với đầy đủ bằng chứng. Tuy nhiên, cần tránh reinterpretation các con số:

- ID Preserved Score ≠ overall accuracy
- 0 confirmed ID switches ≠ zero errors
- Provisional ≠ incorrect

---

### 3.5 Tầng 5 — Trajectory

**Trạng thái:** Đã triển khai và kiểm định

**Bằng chứng triển khai:**
- Trajectory artifact: `outputs/trajectory.json`
- 25 trajectories
- 4,532 observations
- 25 unique track_ids
- Frame range: 1–621
- global_id coverage: 4,532/4,532 (100%)

**Bằng chứng đánh giá:**
- [PIPELINE_EVIDENCE_CLOSURE.md](docs/PIPELINE_EVIDENCE_CLOSURE.md): Trajectory validated

**Thông số kỹ thuật:**

| Metric | Value |
|--------|-------|
| Trajectories | 25 |
| Observations | 4,532 |
| Unique track_ids | 25 |
| Global_id coverage | 4,532 / 4,532 (100%) |
| Frame range | 1–621 |
| Duplicate (track_id, frame_id) pairs | 0 |
| Temporal gaps | 11 |
| Timestamp ordering | PASS |
| GT identity leakage | NO |
| Cross-artifact consistency | PASS |

**Thiết kế quan trọng:**
- `track_id` là primary key của trajectory
- `global_id` được lưu **per observation** (observation-level identity field)
- Thiết kế này tách biệt rõ ràng giữa track continuity và global identity confirmation

**Hạn chế:**
- 11 temporal gaps được ghi nhận
- Không có ground truth trajectory cho validation
- Trajectory validation chỉ xác nhận cấu trúc data, không phải physical correctness

**Đánh giá:** Trajectory đã được triển khai và kiểm định về mặt cấu trúc. Không nên suy luận physical correctness từ trajectory continuity.

---

## 4. Dependency Analysis

### 4.1 Dependency Matrix

| Tầng | Phụ thuộc vào | Điều kiện tiên quyết | Trạng thái |
|-------|---------------|---------------------|-------------|
| 1 | - | Video source | ✅ Sẵn sàng |
| 2 | 1 | YOLO model + config | ✅ Sẵn sàng |
| 3 | 2 | Detection output | ✅ Sẵn sàng |
| 4 | 3 | Tracking output | ✅ Sẵn sàng |
| 5 | 3, 4 | Tracking + Global Identity | ✅ Sẵn sàng |

### 4.2 Rủi ro phụ thuộc ẩn

1. **Tầng 4 phụ thuộc vào Tầng 3**: Global Identity evaluation sử dụng tracking output từ ByteTrack. Nếu tracking thay đổi, Global Identity cần được re-evaluate.

2. **Tầng 5 phụ thuộc vào Tầng 4**: Trajectory chứa global_id per observation. Nếu Global Identity thay đổi, trajectory artifact cần được cập nhật.

3. **Unmatched observations**: 1,976/4,015 (49.2%) runtime observations không khớp với GT. Điều này ảnh hưởng đến downstream evaluation nhưng không ảnh hưởng đến pipeline execution.

4. **Hạn chế detection propagate**: Detection limitations (false positives, false negatives, class confusion) propagate vào tracking và downstream layers.

---

## 5. Evidence Maturity

### 5.1 Maturity Classification

| Evidence Type | Tầng | Maturity Level |
|---------------|------|----------------|
| Video source | 1 | ✅ Runtime-tested |
| Ground Truth | 1 | ⚠️ Documented + Partial implementation |
| Model weights | 2 | ✅ Runtime-tested |
| Detection config | 2 | ✅ Runtime-tested |
| Detection evaluation | 2 | ✅ Experimentally evaluated |
| Tracking code | 3 | ✅ Runtime-tested |
| Tracking evaluation | 3 | ✅ Experimentally evaluated |
| Global Identity code | 4 | ✅ Runtime-tested |
| Global Identity evaluation | 4 | ✅ Independently audited + Closed |
| Trajectory artifact | 5 | ✅ Runtime-tested + Validated |

### 5.2 Tổng hợp

- **Strong evidence**: Tầng 1–5 (implementation + evaluation)
- **Downstream layers**: Tầng 6–9 thuộc định hướng mở rộng, chưa thuộc phạm vi đánh giá hiện tại

---

## 6. Scientific Consistency

### 6.1 Consistency Check

| Source A | Source B | Conflict | Impact |
|----------|----------|----------|--------|
| PIPELINE_EVIDENCE_CLOSURE.md | GI_10_SANITY_AUDIT_CLOSURE.md | None | Consistent |
| GI_08_EVALUATION_CLOSURE.md | outputs/global_identity.json | None | Consistent |
| GI_08 (0 confirmed ID switches) | General claim of perfect identity | N/A | Clarification needed in documentation |

### 6.2 Terminology Consistency Issues

**Issues identified:**

1. **track_id vs global_id**: Đã được phân biệt rõ ràng trong documentation
   - `track_id`: Runtime identity từ ByteTrack
   - `global_id`: Identity từ Global Identity layer

2. **IDSW = 0**: Cần giải thích rõ ràng trong documentation
   - IDSW = 0 theo evaluator convention
   - Không chứng minh perfect physical identity preservation
   - Chỉ áp dụng cho track_id changes

3. **Provisional status**: Cần ngữ cảnh
   - Provisional = insufficient association evidence
   - Không = incorrect identity

### 6.3 Outdated Status Claims

Không tìm thấy claims mâu thuẫn giữa documentation và actual evidence. Tất cả closure documents đều được cập nhật với evidence freeze status.

---

## 7. Terminology Consistency

### 7.1 Key Terms

| Term | Definition | Usage |
|------|------------|-------|
| Detection | YOLOv8m object detection | Tầng 2 |
| Tracking | ByteTrack multi-object tracking | Tầng 3 |
| track_id | Runtime identity từ ByteTrack | Tầng 3 |
| Global Identity | Cross-track identity assignment | Tầng 4 |
| global_id | Identity từ Global Identity registry | Tầng 4 |
| Trajectory | Temporal sequence of observations | Tầng 5 |
| Ground Truth | Annotated data for evaluation | Tầng 1 |
| Runtime artifact | Output từ pipeline execution | All tiers |
| Evaluation | Scientific assessment | Tầng 2, 3, 4 |
| Validation | Structural/technical verification | Tầng 1, 5 |
| Closure | Formal project boundary | Tầng 4 |

### 7.2 Assessment

Terminology sử dụng nhất quán trong documentation. Các terms quan trọng đã được định nghĩa rõ ràng trong closure documents.

---

## 8. Research Scope Consistency

### 8.1 Title vs Implementation

**Title:** "Ứng dụng YoLov8 để phân tích và theo dõi lưu lượng giao thông theo thời gian thực"

**Phạm vi nghiên cứu hiện tại:** Tầng 1–5 (kết thúc tại Trajectory)

**Đã triển khai trong phạm vi:**
- ✅ Video source và temporal sampling
- ✅ YOLOv8 detection
- ✅ ByteTrack tracking
- ✅ Global Identity
- ✅ Trajectory construction

**Chưa thuộc phạm vi đánh giá hiện tại:**
- ROI Events (Tầng 6)
- Traffic State (Tầng 6)
- Spatio-Temporal Graph (Tầng 7)
- Traffic Flow Analysis (Tầng 8)
- Real-time Evaluation (Tầng 9)

### 8.2 Scope Assessment

**Current scope end:** Trajectory (Tầng 5)

**Các tầng downstream (6–9):** Không thuộc phạm vi đánh giá hiện tại

---

## 9. Contribution Assessment

### 9.1 Contributions within Current Scope (Tiers 1–5)

| Contribution | Maturity | Description |
|--------------|----------|-------------|
| Data and Ground Truth construction | **Under construction** | Video, temporal sampling, annotation protocol |
| YOLOv8 detection baseline | **Established** | Implemented + evaluated + frozen |
| ByteTrack tracking | **Established** | Implemented + evaluated |
| Global Identity | **Established** | Implemented + evaluated + closed |
| Global Identity → Trajectory integration | **Established** | Per-observation global_id attachment |
| Trajectory construction | **Implemented** | 25 trajectories, 4532 observations |
| Evaluation methodology | **Established** | Dedicated GI evaluation and audit |

### 9.2 Summary

**Contributions in current scope:**
- Data foundation and temporal sampling methodology
- YOLOv8-based object detection pipeline
- ByteTrack-based multi-object tracking
- Runtime Global Identity layer with registry
- Global Identity evaluation and audit methodology
- Auditable trajectory representation containing per-observation global_id

---

## 10. Current Limitations

Chỉ thảo luận các hạn chế thuộc Tiers 1–5:

### Data Limitations (Tầng 1)
- Annotation chưa hoàn thành theo specification
- Chưa có detection ground truth đầy đủ
- Dataset split chưa được thực thi rõ ràng

### Detection Limitations (Tầng 2)
- Detection precision/recall không đạt mức cao
- Small object detection challenges
- Class confusion đã được ghi nhận

### Tracking Limitations (Tầng 3)
- Không có Re-ID / appearance-based matching
- IDSW = 0 theo convention cụ thể

### Global Identity Limitations (Tầng 4)
- 5 provisional identities (không đủ bằng chứng)
- 3 merge cases
- 1,976 unmatched runtime observations (49.2%)
- Không có appearance-based Re-ID

### Trajectory Limitations (Tầng 5)
- 11 temporal gaps
- Không có ground truth trajectory validation
- Chỉ xác nhận cấu trúc, không phải physical correctness

---

## 11. Overall External Review

### A. Is the project structurally coherent?

**Có.** Kiến trúc 5 tầng được xác định rõ ràng với dependencies hợp lý. Tầng 1→5 flow từ data foundation đến trajectory một cách logical.

### B. Is the current architecture internally consistent?

**Có.** Các tầng có separation of concerns rõ ràng. Dependencies được xác định trong PIPELINE_EVIDENCE_CLOSURE. Không có circular dependencies.

### C. Which layers have strong implementation/evidence?

- **Strong**: Tầng 2 (Detection), Tầng 3 (Tracking), Tầng 4 (Global Identity), Tầng 5 (Trajectory)
- **Partial**: Tầng 1 (Database foundation)

### D. Are there contradictions between documentation and evidence?

**Không.** Documentation nhất quán với evidence.

### E. Is the current project state suitable as a basis for a scientific report?

**Có.** Dự án có đủ evidence cho:
- Detection baseline
- Tracking baseline
- Global Identity methodology và results
- Trajectory construction
- Evaluation methodology

### F. What question does this assessment answer?

> **"Đến thời điểm hiện tại, dự án đã xây dựng và kiểm định nền tảng nghiên cứu từ dữ liệu đầu vào đến biểu diễn quỹ đạo ở mức độ nào?"**

---

## 12. Evidence Sources

### 12.1 Documentation

| Document | Purpose |
|----------|---------|
| [docs/PHASE_1_1_COMPLETION_REPORT.md](docs/PHASE_1_1_COMPLETION_REPORT.md) | Configuration baseline |
| [docs/PHASE_1_3A_GROUND_TRUTH_SPEC.md](docs/PHASE_1_3A_GROUND_TRUTH_SPEC.md) | Data specification |
| [docs/GI_08_DECISION_RECORD.md](docs/GI_08_DECISION_RECORD.md) | Global Identity decisions |
| [docs/GI_08_EVALUATION_CLOSURE.md](docs/GI_08_EVALUATION_CLOSURE.md) | GI evaluation results |
| [docs/GI_10_SANITY_AUDIT_CLOSURE.md](docs/GI_10_SANITY_AUDIT_CLOSURE.md) | GI structural audit |
| [docs/PIPELINE_EVIDENCE_CLOSURE.md](docs/PIPELINE_EVIDENCE_CLOSURE.md) | Pipeline closure |

### 12.2 Runtime Artifacts

| Artifact | Content |
|----------|---------|
| `outputs/global_identity.json` | 15 global IDs (10 confirmed, 5 provisional) |
| `outputs/trajectory.json` | 25 trajectories, 4532 observations |
| `annotation/data/tracking_ground_truth.json` | Ground truth annotations |

### 12.3 Evaluation Outputs

| Output | Scope |
|--------|-------|
| `evaluation/outputs/d03-baseline-10-*/` | Detection evaluation |

---

## 13. Validation Checklist

- [x] Assessment document created
- [x] Tiers 1–5 fully assessed
- [x] Tầng 5 Trajectory marked as implemented/validated per evidence
- [x] Global Identity remains closed
- [x] GI-08 results unchanged
- [x] GI-10 results unchanged
- [x] Downstream layers (6-9) not assessed as current implementation
- [x] Report clearly states current scope ends at Trajectory
- [x] No new numerical results introduced
- [x] Current limitations discussed within Tiers 1-5 only

---

## 14. Restrictions Confirmed

- ❌ No source code modified
- ❌ No tests modified
- ❌ No datasets modified
- ❌ No annotations modified
- ❌ No GT modified
- ❌ No runtime artifacts modified
- ❌ No commits created
- ❌ No methodology decisions made on behalf of Human Project Owner
- ❌ No implementation recommendations

---

RESULT: PASS
ASSESSMENT_UPDATED: docs/PROJECT_OVERVIEW_ASSESSMENT.md
ACTIVE_LAYERS_ASSESSED: 1-5
CURRENT_SCOPE_END: TRAJECTORY
TIER_1_STATUS: Đang xây dựng/kiểm định
TIER_2_STATUS: Đã có baseline, đang đánh giá
TIER_3_STATUS: Đã có pipeline, đã đánh giá
TIER_4_STATUS: Đã triển khai, đánh giá và đóng
TIER_5_STATUS: Đã triển khai và kiểm định
DOWNSTREAM_LAYERS: OUT_OF_CURRENT_SCOPE
GI_08_RESULTS_MODIFIED: NO
GI_10_RESULTS_MODIFIED: NO
IMPLEMENTATION_CHANGES: NONE
METHODOLOGY_CHANGES: NONE
RUNTIME_CHANGES: NONE
GT_CHANGES: NONE
