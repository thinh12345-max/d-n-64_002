import cv2
import numpy as np
from ultralytics import YOLO

VIDEO_PATH = "public/4.mp4"
CONF_THRES = 0.25

ROI = [(100, 50), (100, 480), (900, 500), (900, 50)]

model = YOLO("best.pt")
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
    
    # Chỉ xử lý vài frame để debug
    if frame_count > 100:
        break

    results = model.track(frame, persist=True, conf=0.2, iou=0.5, imgsz=1088, tracker="bytetrack.yaml", verbose=False)

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

            # Vẽ box với màu khác nhau tùy theo inside ROI hay không
            color = (0, 255, 0) if inside_roi(curr_pt) else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{label} {int(track_id)}", (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # In thông tin
            print(f"Frame {frame_count}: {label} ID={int(track_id)}, conf={conf:.2f}, "
                  f"box=({x1},{y1},{x2},{y2}), inside_roi={inside_roi(curr_pt)}, "
                  f"size=({w}x{h})")

    # Vẽ ROI
    cv2.polylines(frame, [np.array(ROI, np.int32)], True, (0, 0, 255), 2)
    cv2.imshow("DEBUG - Green=Inside ROI, Red=Outside", frame)
    
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
print(f"Total frames processed: {frame_count}")
