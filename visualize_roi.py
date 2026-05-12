import cv2
import numpy as np
from ultralytics import YOLO

VIDEO_PATH = "public/4.mp4"

# ROI hiện tại
ROI = [(200, 250), (200, 400), (950, 450), (950, 200)]

model = YOLO("runs/detect/train-10/weights/best.pt")
cap = cv2.VideoCapture(VIDEO_PATH)

# Lấy frame đầu tiên
ret, frame = cap.read()
if ret:
    frame = cv2.resize(frame, (1020, 500))
    
    # Vẽ ROI trên frame
    cv2.polylines(frame, [np.array(ROI, np.int32)], True, (0, 0, 255), 3)
    cv2.putText(frame, "ROI Zone", (400, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # In tọa độ các điểm
    for i, pt in enumerate(ROI):
        cv2.circle(frame, pt, 5, (0, 255, 0), -1)
        cv2.putText(frame, f"P{i}{pt}", pt[0]-30, pt[1]-20, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1) # type: ignore
    
    cv2.imshow("ROI Visualization", frame)
    print("ROI coordinates:", ROI)
    print("Press any key to exit")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

cap.release()
