import cv2
import os
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

video_path = "public/2.mp4"
output_folder = "frames_filtered"

os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)

saved_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)

    boxes = results[0].boxes

    if boxes is not None and len(boxes) > 0:
        filename = f"{output_folder}/frame_{saved_count}.jpg"
        cv2.imwrite(filename, frame)
        saved_count += 1

cap.release()

print("Frame sau khi lọc:", saved_count)