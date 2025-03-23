import cv2
import numpy as np
from ultralytics import YOLO
import time

# Load YOLO model
model_path = 'best (2).pt'
model = YOLO(model_path)

# Define colors for each class
class_colors = {chr(i): (0, 255, 0) for i in range(65, 91)}  # Green for A-Z
flash_color = (0, 0, 255)  # Red for flashing

def enhance_image(frame, brightness=1.0, contrast=1.5, saturation=0.5):
    """
    Enhance the image by adjusting brightness, contrast, and saturation.
    """
    enhanced = frame.astype(float)
    enhanced = enhanced * brightness
    enhanced = (enhanced - 128) * contrast + 128
    hsv = cv2.cvtColor(np.clip(enhanced, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = hsv[:, :, 1] * saturation
    enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return np.clip(enhanced, 0, 255).astype(np.uint8)

def detect_signs(frame):
    """
    Perform YOLO detection on the frame and return results.
    """
    results = model(frame, conf=0.25)
    detected_signs = []
    num_hands = 0
    boxes_data = []

    for result in results:
        boxes = result.boxes.cpu().numpy()
        for box in boxes:
            r = box.xyxy[0].astype(int)
            cls = int(box.cls[0])
            conf = box.conf[0]
            if conf > 0.5:
                class_name = model.names[cls]
                detected_signs.append(class_name)
                num_hands += 1
                boxes_data.append((r, class_name, conf))

    return detected_signs, num_hands, boxes_data

def translate_signs(detected_signs, word_state):
    """
    Translate detected signs into a word.
    """
    word, current_sign, last_sign, hand_shown, last_detection_time, flash_start_time, last_sign_time = word_state

    current_time = time.time()
    if not detected_signs and hand_shown:
        if current_time - last_detection_time > no_sign_threshold:
            word += " "
            hand_shown = False
            last_detection_time = current_time
            current_sign = None

    if len(detected_signs) > 1 and word:
        word = word[:-1]
        hand_shown = False
        current_sign = None

    if detected_signs:
        latest_sign = detected_signs[0]
        if latest_sign != current_sign and current_time - last_sign_time > cooldown_duration:
            word += latest_sign
            current_sign = latest_sign
            hand_shown = True
            last_sign = latest_sign
            last_detection_time = current_time
            flash_start_time = current_time
            last_sign_time = current_time
        elif latest_sign == current_sign and latest_sign == last_sign and current_time - last_sign_time > cooldown_duration:
            word += latest_sign
            last_detection_time = current_time
            flash_start_time = current_time
            last_sign_time = current_time

    return word, current_sign, last_sign, hand_shown, last_detection_time, flash_start_time, last_sign_time

# Constants for translation logic
no_sign_threshold = 5
flash_duration = 0.1
cooldown_duration = 2