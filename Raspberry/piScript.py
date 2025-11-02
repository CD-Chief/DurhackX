# raspberry/main.py
import cv2
import threading
import time
import requests
import json
import base64
import numpy as np
import os
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

# --- CONFIGURATION ---
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables!")

PI_HOST = os.getenv('PI_HOST', '0.0.0.0')
PI_PORT = int(os.getenv('PI_PORT', 5000))
LLM_INTERVAL_SECONDS = int(os.getenv('LLM_INTERVAL_SECONDS', 15))

# --- FLASK SETUP ---
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- GLOBAL VARIABLES ---
servo_angle = 90
running = True
current_frame = None
frame_lock = threading.Lock()
last_llm_summary = "Waiting for initial scene analysis..."
llm_summary_lock = threading.Lock()

# --- SIMPLE OBJECT DETECTION (Optional - can be disabled) ---
class SimpleObjectDetector:
    def __init__(self):
        self.detected_objects = []
        self.use_detection = False  # Set to True if you download models
        
        # Uncomment if you have MobileNet models downloaded
        # try:
        #     self.net = cv2.dnn.readNetFromCaffe(
        #         'models/MobileNetSSD_deploy.prototxt',
        #         'models/MobileNetSSD_deploy.caffemodel'
        #     )
        #     self.use_detection = True
        #     print("[Pi] Object detection enabled")
        # except:
        #     print("[Pi] Object detection models not found. Using LLM only.")
        
        self.classes = ["background", "aeroplane", "bicycle", "bird", "boat",
                       "bottle", "bus", "car", "cat", "chair", "cow",
                       "diningtable", "dog", "horse", "motorbike", "person",
                       "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
    
    def detect(self, frame):
        """Detect objects in frame (disabled by default)"""
        if not self.use_detection:
            return []
        
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5
        )
        
        self.net.setInput(blob)
        detections = self.net.forward()
        
        results = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > 0.5:
                idx = int(detections[0, 0, i, 1])
                class_name = self.classes[idx]
                
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                
                results.append({
                    'class': class_name,
                    'confidence': float(confidence),
                    'box': [startX, startY, endX, endY]
                })
        
        self.detected_objects = results
        return results
    
    def draw_detections(self, frame):
        """Draw bounding boxes on frame"""
        for obj in self.detected_objects:
            startX, startY, endX, endY = obj['box']
            label = f"{obj['class']}: {obj['confidence']:.2f}"
            
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
            cv2.putText(frame, label, (startX, startY - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame

detector = SimpleObjectDetector()

# --- LLM FUNCTIONS ---
def cv2_to_base64_image_url(cv2_img):
    """Converts an OpenCV BGR image to a base64 encoded data URL."""
    if cv2_img is None or cv2_img.size == 0:
        raise ValueError("Input OpenCV image is empty or None.")
    
    _, buffer = cv2.imencode('.jpg', cv2_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    base64_string = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_string}"

def get_gemini_description(image_cv2, user_request_prompt=None):
    """Sends the image and a prompt to the Gemini 2.0 Flash model via OpenRouter."""
    try:
        image_data_url = cv2_to_base64_image_url(image_cv2)
        
        system_instruction_prompt = """
        You are an AI assistant providing objective, factual descriptions of visual scenes.
        Your output must ONLY be based on what is directly observable in the provided image.
        Be concise, accurate, and focus strictly on visible objects, people, actions, and the overall scene.
        Provide 1-2 sentence descriptions connecting observations naturally.
        """
        
        if user_request_prompt:
            actual_user_prompt = f"Based ONLY on the image, answer this question concisely: '{user_request_prompt}'."
        else:
            actual_user_prompt = "Provide a factual description of everything visible in this image in 1-2 sentences, connecting the observations naturally."
        
        messages_payload = [
            {"role": "system", "content": system_instruction_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": actual_user_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}}
                ]
            }
        ]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = json.dumps({
            "model": "google/gemini-2.0-flash-001",
            "messages": messages_payload,
        })
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=data,
            timeout=30
        )
        
        response.raise_for_status()
        response_json = response.json()
        llm_text_output = response_json['choices'][0]['message']['content'].strip()
        
        return llm_text_output
    
    except requests.exceptions.Timeout:
        return "AI analysis timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "Error: Invalid API key."
        elif e.response.status_code == 429:
            return "Error: API rate limit exceeded. Please wait."
        else:
            return f"Error: API returned status {e.response.status_code}"
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

# --- CAMERA THREAD ---
def camera_thread_func():
    global current_frame, running
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Pi] Error: Could not open camera")
        running = False
        return
    
    print("[Pi] Camera started")
    
    while running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        
        # Optionally detect objects (if models are available)
        detector.detect(frame)
        frame = detector.draw_detections(frame)
        
        # Add servo angle overlay
        cv2.putText(frame, f"Servo: {servo_angle}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        with frame_lock:
            current_frame = frame.copy()
        
        time.sleep(0.03)  # ~30 FPS
    
    cap.release()

# --- LLM ANALYSIS THREAD ---
last_llm_trigger_time = time.time()

def llm_thread_func():
    global last_llm_summary, last_llm_trigger_time, running
    
    print("[Pi] LLM analysis thread started")
    time.sleep(5)  # Wait for camera to initialize
    
    while running:
        if time.time() - last_llm_trigger_time >= LLM_INTERVAL_SECONDS:
            frame_to_analyze = None
            
            with frame_lock:
                if current_frame is not None:
                    frame_to_analyze = current_frame.copy()
            
            if frame_to_analyze is not None:
                print("[Pi] Running LLM analysis...")
                llm_response = get_gemini_description(frame_to_analyze)
                
                with llm_summary_lock:
                    last_llm_summary = llm_response
                
                print(f"[Pi] LLM: {llm_response}")
                
                # Emit to frontend via WebSocket
                socketio.emit('llm_update', {'summary': llm_response})
                
                last_llm_trigger_time = time.time()
        
        time.sleep(1)

# --- FLASK ROUTES ---
def generate_frames():
    """Generate video frames for streaming"""
    while True:
        frame_to_send = None
        
        with frame_lock:
            if current_frame is not None:
                frame_to_send = current_frame.copy()
        
        if frame_to_send is not None:
            ret, buffer = cv2.imencode('.jpg', frame_to_send, 
                                      [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    """Stream Pi camera feed"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/orientation', methods=['POST'])
def receive_orientation():
    """Receive orientation from laptop"""
    global servo_angle
    
    data = request.json
    yaw = data.get('yaw', 0)
    pitch = data.get('pitch', 0)
    
    # Convert yaw to servo angle (map -45 to 45 degrees → 0 to 180)
    servo_angle = int(90 + yaw)
    servo_angle = max(0, min(180, servo_angle))
    
    # TODO: Send to actual servo hardware here
    # Example: GPIO.output(SERVO_PIN, servo_angle)
    
    return jsonify({'status': 'ok', 'servo_angle': servo_angle})

@app.route('/llm_summary')
def get_llm_summary():
    """Get latest LLM description"""
    with llm_summary_lock:
        return jsonify({'summary': last_llm_summary})

@app.route('/analyze', methods=['POST'])
def trigger_analysis():
    """Manually trigger LLM analysis"""
    global last_llm_trigger_time
    
    frame_to_analyze = None
    
    with frame_lock:
        if current_frame is not None:
            frame_to_analyze = current_frame.copy()
    
    if frame_to_analyze is not None:
        data = request.json or {}
        user_prompt = data.get('prompt', None)
        
        llm_response = get_gemini_description(frame_to_analyze, user_prompt)
        
        with llm_summary_lock:
            last_llm_summary = llm_response
        
        # Emit via WebSocket
        socketio.emit('llm_update', {'summary': llm_response})
        
        # Reset timer
        last_llm_trigger_time = time.time()
        
        return jsonify({'summary': llm_response})
    
    return jsonify({'error': 'No frame available'}), 400

@app.route('/status')
def status():
    """Get system status"""
    return jsonify({
        'servo_angle': servo_angle,
        'camera_active': current_frame is not None,
        'llm_active': True
    })

# --- MAIN ---
if __name__ == "__main__":
    print("[Pi] Starting Raspberry Pi Camera System...")
    print("[Pi] API Key configured:", "✓" if OPENROUTER_API_KEY else "✗")
    
    # Start threads
    threading.Thread(target=camera_thread_func, daemon=True).start()
    threading.Thread(target=llm_thread_func, daemon=True).start()
    
    print(f"[Pi] Pi camera system running on http://{PI_HOST}:{PI_PORT}")
    print("[Pi] Ready to receive orientation from laptop")
    print(f"[Pi] LLM analysis will run every {LLM_INTERVAL_SECONDS} seconds")
    
    try:
        socketio.run(app, host=PI_HOST, port=PI_PORT, debug=False)
    except KeyboardInterrupt:
        print("[Pi] Shutting down...")
        running = False
    finally:
        print("[Pi] Exited")
