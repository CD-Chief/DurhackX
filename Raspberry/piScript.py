# raspberry/unified_main.py
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
from gpiozero import AngularServo

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

# --- CONFIGURATION ---
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    print("[Pi] Warning: OPENROUTER_API_KEY not found. AI features disabled.")
    OPENROUTER_API_KEY = None

PI_HOST = os.getenv('PI_HOST', '0.0.0.0')
PI_PORT = int(os.getenv('PI_PORT', 5000))
LLM_INTERVAL_SECONDS = int(os.getenv('LLM_INTERVAL_SECONDS', 15))

# --- SERVO SETUP ---
SERVO_PIN = 2  # BCM pin 2 (physical pin 3)

# Create servo object (no factory needed)
servo = AngularServo(
    SERVO_PIN,
    min_angle=0,
    max_angle=180,
    min_pulse_width=0.5/1000,
    max_pulse_width=2.5/1000
)

servo.angle = 90  # Start at neutral

# --- FLASK SETUP ---
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- GLOBAL VARIABLES ---
servo_angle = 90
last_commanded_angle = 90  # Track last angle sent to servo
running = True
current_frame = None
frame_lock = threading.Lock()
last_llm_summary = "Waiting for initial scene analysis..."
llm_summary_lock = threading.Lock()

# Servo deadband - ignore changes smaller than this
SERVO_DEADBAND = 2  # degrees

# --- SERVO CONTROL FUNCTIONS ---
def set_servo_angle(angle):
    """Set servo to specific angle (0-180)"""
    try:
        # Clamp angle to valid range
        angle = max(0, min(180, angle))
        servo.angle = angle
        print(f"[Pi] Servo Angle: {angle:.1f}°   ", end="\r")
    except Exception as e:
        print(f"\n[Pi] Servo error: {e}")

# --- LLM FUNCTIONS ---
def cv2_to_base64_image_url(cv2_img):
    """Converts an OpenCV BGR image to a base64 encoded data URL."""
    if cv2_img is None or cv2_img.size == 0:
        raise ValueError("Input OpenCV image is empty or None.")
    
    _, buffer = cv2.imencode('.jpg', cv2_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    base64_string = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_string}"

def get_gemini_description(image_cv2):
    """Sends the image to Gemini via OpenRouter."""
    if not OPENROUTER_API_KEY:
        return "AI features disabled (no API key)"
    
    try:
        image_data_url = cv2_to_base64_image_url(image_cv2)
        
        system_instruction = """
        You are an AI assistant providing objective, factual descriptions of visual scenes.
        Be concise and accurate. Provide 1-2 sentence descriptions.
        """
        
        user_prompt = "Describe everything visible in this image in 1-2 sentences."
        
        messages_payload = [
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
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
        return response_json['choices'][0]['message']['content'].strip()
    
    except Exception as e:
        return f"AI analysis error: {str(e)[:50]}"

# --- CAMERA THREAD ---
def camera_thread_func():
    global current_frame, running
    
    try:
        # Try Picamera2 first (Raspberry Pi camera module)
        from picamera2 import Picamera2
        picam = Picamera2()
        picam.configure(picam.create_preview_configuration(main={"size": (640, 480)}))
        picam.start()
        time.sleep(2)
        print("[Pi] Using Picamera2")
        
        while running:
            frame = picam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Add servo angle overlay
            cv2.putText(frame, f"Servo: {servo_angle}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            with frame_lock:
                current_frame = frame.copy()
            
            time.sleep(0.03)  # ~30 FPS
        
        picam.stop()
        
    except ImportError:
        # Fallback to USB webcam
        print("[Pi] Picamera2 not available, using USB webcam")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[Pi] Error: Could not open camera")
            running = False
            return
        
        while running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Add servo angle overlay
            cv2.putText(frame, f"Servo: {servo_angle}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            with frame_lock:
                current_frame = frame.copy()
            
            time.sleep(0.03)
        
        cap.release()

# --- LLM ANALYSIS THREAD ---
last_llm_trigger_time = time.time()

def llm_thread_func():
    global last_llm_summary, last_llm_trigger_time, running
    
    print("[Pi] LLM analysis thread started")
    time.sleep(5)
    
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
    """Receive orientation from laptop and move servo"""
    global servo_angle, last_commanded_angle
    
    data = request.json
    yaw = data.get('yaw', 0)
    pitch = data.get('pitch', 0)
    
    # DEBUG: Print what we received
    print(f"\n[Pi] Received from laptop: yaw={yaw:.2f}°, pitch={pitch:.2f}°")
    
    # Convert yaw to servo angle (map -45 to 45 degrees → 0 to 180)
    new_angle = int(90 + yaw)
    new_angle = max(0, min(180, new_angle))
    
    # Only move servo if change is significant (deadband)
    angle_change = abs(new_angle - last_commanded_angle)
    
    if angle_change >= SERVO_DEADBAND:
        print(f"[Pi] Moving servo: {last_commanded_angle}° → {new_angle}° (change: {angle_change}°)")
        servo_angle = new_angle
        last_commanded_angle = new_angle
        set_servo_angle(servo_angle)
    else:
        print(f"[Pi] Ignoring small change: {angle_change}° (deadband: {SERVO_DEADBAND}°)")
    
    return jsonify({
        'status': 'ok', 
        'servo_angle': last_commanded_angle, 
        'received_yaw': yaw, 
        'received_pitch': pitch,
        'angle_change': angle_change
    })

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
        llm_response = get_gemini_description(frame_to_analyze)
        
        with llm_summary_lock:
            last_llm_summary = llm_response
        
        socketio.emit('llm_update', {'summary': llm_response})
        last_llm_trigger_time = time.time()
        
        return jsonify({'summary': llm_response})
    
    return jsonify({'error': 'No frame available'}), 400

@app.route('/status')
def status():
    """Get system status"""
    return jsonify({
        'servo_angle': servo_angle,
        'camera_active': current_frame is not None,
        'llm_active': OPENROUTER_API_KEY is not None
    })

# --- MAIN ---
if __name__ == "__main__":
    print("[Pi] Starting 3rd Eye Raspberry Pi System...")
    print("[Pi] API Key configured:", "✓" if OPENROUTER_API_KEY else "✗ (AI disabled)")
    
    # Start threads
    threading.Thread(target=camera_thread_func, daemon=True).start()
    
    if OPENROUTER_API_KEY:
        threading.Thread(target=llm_thread_func, daemon=True).start()
    
    print(f"[Pi] System running on http://{PI_HOST}:{PI_PORT}")
    print("[Pi] Ready to receive orientation from laptop")
    if OPENROUTER_API_KEY:
        print(f"[Pi] LLM analysis will run every {LLM_INTERVAL_SECONDS} seconds")
    
    try:
        socketio.run(app, host=PI_HOST, port=PI_PORT, debug=False)
    except KeyboardInterrupt:
        print("[Pi] Shutting down...")
        running = False
    finally:
        servo.close()
        print("[Pi] Exited cleanly")
