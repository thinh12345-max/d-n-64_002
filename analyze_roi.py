import cv2
import numpy as np
from ultralytics import YOLO

VIDEO_PATH = "public/4.mp4"

# ROI cũ không hợp lệ: [(513, 76), (211, 298), (925, 369), (511, 77)]
# Điểm 1 (513, 76) và điểm 4 (511, 77) gần như trùng nhau

# Tạo ROI đúng - vẽ hình tứ giác có 4 góc
cap = cv2.VideoCapture(VIDEO_PATH)
ret, frame = cap.read()
cap.release()

if ret:
    frame = cv2.resize(frame, (1020, 500))
    # Hiển thị frame để xác định ROI
    cv2.imshow("Select ROI - Identify counting area", frame)
    print("Frame đã hiển thị. Hãy quan sát và xác định ROI corners")
    print("ROI cũ: [(513, 76), (211, 298), (925, 369), (511, 77)]")
    print("Nhận xét: Điểm 1 (513,76) và điểm 4 (511,77) gần trùng - tạo hình invalid!")
    print("\nROI đúng nên là 4 góc của một tứ giác:")
    print("- Top-left: (211, 298)")
    print("- Top-right: (925, 369)")  
    print("- Bottom-right: (513, 76)?")
    print("- Bottom-left: ???")
    print("\nHãy định nghĩa lại ROI với 4 góc rõ ràng!")
    
    cv2.waitKey(3000)
    cv2.destroyAllWindows()
