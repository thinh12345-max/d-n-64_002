import cv2
from ultralytics import YOLO

# Kiểm tra các class trong model
model_path = "runs/detect/train-10/weights/best.pt"
model = YOLO(model_path)

print("Model names (classes):")
print(model.names)
print("\nTotal classes:", len(model.names))

# Test với 1 frame để xem output
VIDEO_PATH = "public/4.mp4"
cap = cv2.VideoCapture(VIDEO_PATH)

ret, frame = cap.read()
if ret:
    frame = cv2.resize(frame, (1020, 500))
    results = model.predict(frame, conf=0.2, verbose=False)
    
    if results and len(results) > 0:
        boxes = results[0].boxes
        if boxes is not None:
            classes = boxes.cls.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            
            print("\nDetected classes in first frame:")
            for cls, conf in zip(classes, confs):
                class_idx = int(cls)
                class_name = model.names[class_idx]
                print(f"  Class {class_idx} ({class_name}): {conf:.2f}")

cap.release()
