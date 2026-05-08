import cv2
import numpy as np
from ultralytics import YOLO
import json

VIDEO_PATH = "public/4.mp4"
CONF_THRES = 0.25  # Threshold confidence - thấp để detect nhiều xe hơn

# ROI được định nghĩa lại dựa trên vị trí xe được phát hiện
# Vùng đếm chính: khu vực từ giữa đến phải của frame, phía dưới
# [top-left, bottom-left, bottom-right, top-right]
ROI = [(100, 50), (100, 480), (900, 500), (900, 50)]

model = YOLO("runs/detect/train-10/weights/best.pt")

cap = cv2.VideoCapture(VIDEO_PATH)

track_history = {}
count_ids = set()

# Chỉ đếm các loại xe được model detect
vehicle_count = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}

def inside_roi(point):
    return cv2.pointPolygonTest(np.array(ROI, np.int32), point, False) >= 0

while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.resize(frame, (1020, 500))
    results = model.track(frame, persist=True, conf=CONF_THRES, iou=0.5, imgsz=1080, tracker="bytetrack.yaml", verbose=False)

    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy()
        confs = results[0].boxes.conf.cpu().numpy()
        
        for box, track_id, cls, conf in zip(boxes, ids, classes, confs):
            label = model.names[int(cls)] # type: ignore
            
            # Chỉ xử lý các loại xe có trong vehicle_count
            if label not in vehicle_count:
                continue
                
            x1, y1, x2, y2 = map(int, box)
            w = x2 - x1
            h = y2 - y1

            # Bỏ qua các box quá nhỏ (noise)
            if w < 10 or h < 10:
                continue

            cv2.putText(
                frame,
                f"{label} {conf:.2f}",
                (x1, y1 - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            curr_pt = (cx, y2)  # Sử dụng điểm dưới cùng của box
            
            inside_current = inside_roi(curr_pt)

            # Đơn giản: Đếm bất kỳ ID nào xuất hiện trong ROI (chỉ đếm 1 lần)
            if inside_current:
                if track_id not in count_ids:
                    count_ids.add(track_id)
                    vehicle_count[label] += 1
            
            # Track vị trí cho các frame tiếp theo
            track_history[track_id] = inside_current

    
    cv2.polylines(frame, [np.array(ROI, np.int32)], True, (0, 0, 255), 2)
    y_offset = 30
    for k, v in vehicle_count.items():
        cv2.putText(frame, f"{k.upper()}: {v}", (20, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        y_offset += 25

    cv2.imshow("AI Counting - Optimized", frame)
    if cv2.waitKey(1) == 27: break

cap.release()
cv2.destroyAllWindows()

with open("vehicle_counts.json", "w") as f:
    json.dump(vehicle_count, f, indent=4)

print("--- THỐNG KÊ CUỐI CÙNG ---")
print(vehicle_count)