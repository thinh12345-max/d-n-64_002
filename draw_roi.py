import cv2 
import numpy as np

points = []

def draw_roi(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(points)

cap = cv2.VideoCapture("public/3.mp4")

fps = cap.get(cv2.CAP_PROP_FPS)
delay = int(15000 / fps)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.resize(frame,(1020,500))

    for point in points:
        cv2.circle(frame, point, 5, (0,0,255), -1)

    if len(points) > 1:
        cv2.polylines(frame,[np.array(points)],False,(0,255,255),2)

    cv2.imshow("Draw ROI",frame)

    cv2.setMouseCallback("Draw ROI",draw_roi)  # type: ignore

    if cv2.waitKey(delay) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

print("ROI points:",points)