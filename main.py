from dataclasses import dataclass
from pathlib import Path
import json
import math

import cv2
import numpy as np
from ultralytics import YOLO

# Configuration
BASE_DIR = Path(__file__).resolve().parent
FRAME_SIZE = (1020, 500)
IMGSZ = 1088
OUTPUT_PATH = BASE_DIR / "vehicle_counts.json"
VIDEO_PATH = BASE_DIR / "public" / "4.mp4"
CUSTOM_MODEL_PATH = BASE_DIR / "runs" / "detect" / "train-10" / "weights" / "best.pt"
OUTSIDE_ROI_COLOR = (180, 180, 180)

# Tracker configuration
TRACKER_CONFIG = {
    "stale_frames": 60,
}

# ROI definition for counting area
ROI = [(80, 40), (80, 490), (1000, 500), (1000, 40)]
COUNTABLE_LABELS = ("car", "motorcycle", "bus", "truck")

# Auto-detect classes from custom model
print(f"Loading custom model: {CUSTOM_MODEL_PATH}")
try:
    temp_model = YOLO(str(CUSTOM_MODEL_PATH))
    model_class_names = temp_model.names
    print(f"Model classes: {model_class_names}")
    
    # Create reverse mapping (class_id -> class_name)
    id_to_name = {}
    for class_id, class_name in model_class_names.items():
        name_lower = str(class_name).lower()
        if name_lower in COUNTABLE_LABELS:
            id_to_name[int(class_id)] = name_lower
    print(f"Countable classes mapping: {id_to_name}")
except Exception as e:
    print(f"Error loading model: {e}")
    # Fallback mapping if model loading fails (class_id -> label)
    id_to_name = { 0: "bus", 1: "car", 2: "motorcycle", 3: "truck" }

# Colors for visualization
class_colors = {
    "car": (0, 255, 0),      # Green
    "motorcycle": (0, 255, 255),  # Yellow
    "bus": (255, 255, 0),    # Cyan
    "truck": (255, 0, 255),  # Magenta
}

@dataclass
class EntityState:
    entity_id: int
    last_point: tuple[int, int]
    last_box: tuple[int, int, int, int]
    last_frame: int
    label: str
    confidence: float
    counted: bool = False

def ensure_file_exists(path):
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file: {path}")

def inside_roi(point):
    return cv2.pointPolygonTest(np.array(ROI, np.int32), point, False) >= 0

def box_iou(box_a, box_b):
    """Calculate intersection over union between two boxes"""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union_area = area_a + area_b - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0

def cleanup_tracker_links(tracker_to_entity, entities, frame_index, max_stale=60):
    """Remove stale trackers"""
    stale_trackers = []
    for tracker_key, entity_id in tracker_to_entity.items():
        state = entities.get(entity_id)
        if state is None or frame_index - state.last_frame > max_stale:
            stale_trackers.append(tracker_key)
    
    for key in stale_trackers:
        tracker_to_entity.pop(key, None)

def is_reasonable_match(state, point, box, frame_index, max_distance=50, max_gap=30):
    """Check if match is reasonable based on position and frame gap"""
    frame_gap = frame_index - state.last_frame
    if frame_gap <= 0 or frame_gap > max_gap:
        return False
    
    distance = math.dist(point, state.last_point)
    if distance > max_distance:
        return False
    
    return True

def assign_entity(track_id, point, box, label, frame_index, tracker_to_entity, entities, next_entity_id, matched_entity_ids):
    """Assign entity to existing or create new entity"""
    tracker_key = track_id
    existing_entity_id = tracker_to_entity.get(tracker_key)
    
    if existing_entity_id is not None:
        state = entities.get(existing_entity_id)
        if state is not None and existing_entity_id not in matched_entity_ids:
            if is_reasonable_match(state, point, box, frame_index):
                matched_entity_ids.add(existing_entity_id)
                return existing_entity_id, next_entity_id
        tracker_to_entity.pop(tracker_key, None)
    
    # Find best matching existing entity (same label)
    best_entity_id = None
    best_score = None
    
    for entity_id, state in entities.items():
        if entity_id in matched_entity_ids:
            continue
        if state.label != label:
            continue
        if not is_reasonable_match(state, point, box, frame_index):
            continue
            
        frame_gap = frame_index - state.last_frame
        distance = math.dist(point, state.last_point)
        overlap = box_iou(box, state.last_box)
        score = distance + frame_gap * 2 - overlap * 100
        
        if best_score is None or score < best_score:
            best_score = score
            best_entity_id = entity_id
    
    if best_entity_id is None:
        next_entity_id += 1
        best_entity_id = next_entity_id
        entities[best_entity_id] = EntityState(
            entity_id=best_entity_id,
            last_point=point,
            last_box=box,
            last_frame=frame_index,
            label=label,
            confidence=0.0,
        )
    
    tracker_to_entity[tracker_key] = best_entity_id
    matched_entity_ids.add(best_entity_id)
    return best_entity_id, next_entity_id

def build_counts(entities):
    """Count vehicles that have been counted"""
    counts = {label: 0 for label in COUNTABLE_LABELS}
    for state in entities.values():
        if state.counted:
            counts[state.label] += 1
    return counts


def draw_detection(frame, box, text, color, center_point, inside_current):
    """Draw bounding box and ID label for each tracked vehicle."""
    x1, y1, x2, y2 = box
    thickness = 2 if inside_current else 1
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    cv2.circle(frame, center_point, 4, color, -1)
    cv2.putText(
        frame,
        text,
        (x1, max(20, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        color,
        2,
    )

# Main execution
ensure_file_exists(CUSTOM_MODEL_PATH)
ensure_file_exists(VIDEO_PATH)

model = YOLO(str(CUSTOM_MODEL_PATH))
cap = cv2.VideoCapture(str(VIDEO_PATH))
if not cap.isOpened():
    raise RuntimeError(f"Khong mo duoc video: {VIDEO_PATH}")

# Tracking state
tracker_to_entity = {}  # (track_id) -> entity_id
entities = {}  # entity_id -> EntityState
next_entity_id = 0
frame_index = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    frame_index += 1
    cleanup_tracker_links(tracker_to_entity, entities, frame_index, TRACKER_CONFIG["stale_frames"])
    frame = cv2.resize(frame, FRAME_SIZE)
    matched_entity_ids = set()
    
    # Run tracking with custom model
    result = model.track(
        frame,
        persist=True,
        classes=list(id_to_name.keys()),  # All vehicle classes
        conf=0.15,
        iou=0.45,
        imgsz=IMGSZ,
        tracker="botsort.yaml",
        verbose=False,
    )[0]

    boxes_obj = result.boxes
    if boxes_obj is not None and boxes_obj.id is not None:
        # Convert tensors to numpy arrays safely
        boxes = boxes_obj.xyxy.cpu().numpy() if hasattr(boxes_obj.xyxy, 'cpu') else np.array(boxes_obj.xyxy) # type: ignore
        ids = boxes_obj.id.cpu().numpy() if hasattr(boxes_obj.id, 'cpu') else np.array(boxes_obj.id) # type: ignore
        classes = boxes_obj.cls.cpu().numpy() if hasattr(boxes_obj.cls, 'cpu') else np.array(boxes_obj.cls) # type: ignore
        confs = boxes_obj.conf.cpu().numpy() if hasattr(boxes_obj.conf, 'cpu') else np.array(boxes_obj.conf) # type: ignore

        for box, raw_track_id, cls, conf in zip(boxes, ids, classes, confs):
            class_id = int(cls)
            
            # Get label from our mapping
            label = id_to_name.get(class_id)
            if label is None:
                continue  # Skip classes not in our 4 types
            
            # Parse bounding box
            x1, y1, x2, y2 = map(int, box)
            width = x2 - x1
            height = y2 - y1
            
            # Minimum size filter
            if width < 10 or height < 10:
                continue
                
            # Center point calculation
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            center_point = (int(center_x), int(center_y))
            box_tuple = (x1, y1, x2, y2)
            track_id = int(raw_track_id)
            
            # ROI check uses bottom-center, but we still draw objects outside ROI.
            roi_point = (center_x, y2)  # Using bottom center for ROI check
            inside_current = inside_roi(roi_point)
                
            # Assign entity ID
            entity_id, next_entity_id = assign_entity(
                track_id,
                center_point,
                box_tuple,
                label,
                frame_index,
                tracker_to_entity,
                entities,
                next_entity_id,
                matched_entity_ids,
            )
            
            # Update state
            state = entities[entity_id]
            state.last_point = center_point
            state.last_box = box_tuple
            state.last_frame = frame_index
            state.confidence = conf
            
            # Mark as counted only when object is inside ROI.
            if inside_current and state.confidence >= 0.2 and not state.counted:
                state.counted = True

            color = class_colors.get(label, (128, 128, 128)) if inside_current else OUTSIDE_ROI_COLOR
            draw_detection(
                frame,
                box_tuple,
                f"{label} T{track_id} E{entity_id} {conf:.2f}",
                color,
                center_point,
                inside_current,
            )

    # Build final counts
    vehicle_count = build_counts(entities)

    # Visualization
    cv2.polylines(frame, [np.array(ROI, np.int32)], True, (0, 0, 255), 2)
    y_offset = 30
    for label, count in vehicle_count.items():
        cv2.putText(
            frame,
            f"{label.upper()}: {count}",
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2,
        )
        y_offset += 25

    cv2.imshow("AI Counting - Single Tracker", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()

# Save results
vehicle_count = build_counts(entities)
with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(vehicle_count, f, indent=4)

print("--- THONG KE CUOI CUNG ---")
print(vehicle_count)
