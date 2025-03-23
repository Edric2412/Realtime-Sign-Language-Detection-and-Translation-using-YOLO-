from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import cv2
import numpy as np
import json
import time
from .utils import enhance_image, detect_signs, translate_signs, class_colors, flash_color, no_sign_threshold, flash_duration, cooldown_duration

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Global variables for state management
brightness = 1.0
contrast = 1.5
saturation = 0.5

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the frontend HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time video streaming and translation."""
    await websocket.accept()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Specify the backend
    if not cap.isOpened():
        print("Error: Could not open webcam")
        await websocket.close()
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Initialize state variables
    word = ""
    current_sign = None
    last_sign = None
    hand_shown = False
    last_detection_time = time.time()
    flash_start_time = None
    last_sign_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            # Enhance the frame
            frame = enhance_image(frame, brightness, contrast, saturation)

            # Perform detection
            detected_signs, _, boxes_data = detect_signs(frame)

            # Translate signs
            word_state = (
                word, current_sign, last_sign, hand_shown,
                last_detection_time, flash_start_time, last_sign_time
            )
            word, current_sign, last_sign, hand_shown, last_detection_time, flash_start_time, last_sign_time = translate_signs(detected_signs, word_state)

            # Draw bounding boxes
            for r, class_name, conf in boxes_data:
                color = class_colors.get(class_name, (255, 0, 0))
                if flash_start_time and time.time() - flash_start_time < flash_duration:
                    color = flash_color
                cv2.rectangle(frame, (r[0] + 2, r[1] + 2), (r[2] + 2, r[3] + 2), (0, 0, 0), 2)
                cv2.rectangle(frame, (r[0], r[1]), (r[2], r[3]), color, 2)
                text = f'{class_name} {conf:.2f}'
                (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
                cv2.rectangle(frame, (r[0], r[1] - text_height - 10), (r[0] + text_width + 10, r[1] - 10), (0, 0, 0), -1)
                cv2.putText(frame, text, (r[0] + 5, r[1] - 15), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.9, (255, 255, 255), 2, cv2.LINE_AA)

            # Convert frame to JPEG format
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            # Prepare data to send
            data = {
                "frame": frame_bytes.hex(),
                "translation": word
            }

            # Send data over WebSocket
            await websocket.send_json(data)
            print(f"Sent frame with translation: {word}")  # Debugging statement
    finally:
        cap.release()

@app.post("/adjust-settings/")
async def adjust_settings(data: dict):
    """Endpoint to adjust image enhancement settings."""
    global brightness, contrast, saturation
    brightness = data.get("brightness", brightness)
    contrast = data.get("contrast", contrast)
    saturation = data.get("saturation", saturation)
    return {"message": "Settings updated successfully."}