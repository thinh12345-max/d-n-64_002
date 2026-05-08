import cv2
import numpy as np
from ultralytics import YOLO

VIDEO_PATH = "public/4.mp4"
CONF_THRES = 0.45

ROI = [(513, 76), (211, 298), (925, 369), (511, 77)]

model = YOLO("runs/detect/train-10/weights/best.pt")
cap = cv2.VideoCapture(VIDEO_PATH)

track_history = {}
count_ids = set()
vehicle_count = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}

def inside_roi(point):
    return cv2.pointPolygonTest(np.array(ROI, np.int32), point, False) >= 0

frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.resize(frame, (1020, 500))
    frame_count += 1
    
    if frame_count > 200:
        break

    results = model.track(frame, persist=True, conf=CONF_THRES, iou=0.5, imgsz=1088, tracker="bytetrack.yaml", verbose=False)

    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy()
        confs = results[0].boxes.conf.cpu().numpy()
        
        for box, track_id, cls, conf in zip(boxes, ids, classes, confs):
            label = model.names[int(cls)]
            
            if label not in vehicle_count:
                continue
                
            x1, y1, x2, y2 = map(int, box)
            w = x2 - x1
            h = y2 - y1

            if w < 10 or h < 10:
                continue

            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            curr_pt = (cx, y2)
            
            inside = inside_roi(curr_pt)

            # Debug: In ra tất cả detection, không chỉ các cái được đếm
            if track_id not in track_history:
                track_history[track_id] = curr_pt
                if inside and track_id not in count_ids:
                    count_ids.add(track_id)
                    vehicle_count[label] += 1
                    print(f"Frame {frame_count}: NEW - {label} ID={int(track_id)}, inside_roi={inside}, COUNTED! Total {label}={vehicle_count[label]}")
                else:
                    print(f"Frame {frame_count}: NEW - {label} ID={int(track_id)}, inside_roi={inside}, NOT counted (inside={inside}, in_count_ids={track_id in count_ids})")
            else:
                prev_pt = track_history[track_id]
                prev_inside = inside_roi(prev_pt)
                
                if not prev_inside and inside:
                    if track_id not in count_ids:
                        count_ids.add(track_id)
                        vehicle_count[label] += 1
                        print(f"Frame {frame_count}: CROSSING - {label} ID={int(track_id)}, crossed ROI boundary! Total {label}={vehicle_count[label]}")
                    else:
                        print(f"Frame {frame_count}: CROSSING - {label} ID={int(track_id)}, crossed but already counted")
                else:
                    if frame_count % 50 == 0:  # In ra mỗi 50 frame
                        print(f"Frame {frame_count}: TRACKING - {label} ID={int(track_id)}, inside_roi={inside}, prev_inside={prev_inside}")
                
                track_history[track_id] = curr_pt

cap.release()
cv2.destroyAllWindows()

print("\n=== FINAL COUNT ===")
print(vehicle_count)
