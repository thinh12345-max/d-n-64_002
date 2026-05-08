import cv2
import numpy as np
import json

directions = ["north", "south", "east", "west"]
rois = {direction: [] for direction in directions}
current_direction = 0

def draw_roi(event, x, y, flags, param):
    global current_direction
    if event == cv2.EVENT_LBUTTONDOWN:
        if current_direction < len(directions):
            rois[directions[current_direction]].append((x, y))
            print(f"Added point to {directions[current_direction]}: {x}, {y}")

cap = cv2.VideoCapture("public/4.mp4")

fps = cap.get(cv2.CAP_PROP_FPS)
delay = int(15000 / fps)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame,(1020,500))

    # Vẽ các điểm đã chọn
    for direction, points in rois.items():
        color = (0,255,255) if direction == directions[current_direction] else (255,255,0)
        for point in points:
            cv2.circle(frame, point, 5, color, -1)
        if len(points) > 1:
            cv2.polylines(frame,[np.array(points)],False,color,2)

    # Hiển thị hướng hiện tại
    cv2.putText(frame, f"Current: {directions[current_direction]} - Click to add points", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
    cv2.putText(frame, "Press SPACE to next direction, ESC to save and exit", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

    cv2.imshow("Configure ROI", frame)
    cv2.setMouseCallback("Configure ROI", draw_roi) # type: ignore

    key = cv2.waitKey(delay) & 0xFF
    if key == 27:  # ESC
        break
    elif key == 32:  # SPACE
        current_direction += 1
        if current_direction >= len(directions):
            current_direction = 0

cap.release()
cv2.destroyAllWindows()

# Lưu ROI vào file
with open('roi_config.json', 'w') as f:
    json.dump(rois, f)

print("ROI configuration saved to roi_config.json")
print(rois)