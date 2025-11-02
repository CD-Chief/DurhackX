# laptop/main.py
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
import threading

print("=" * 50)
print("STARTING LAPTOP TRACKER...")
print("=" * 50)

# Import face tracker
from face_tracker import FaceTracker
from communication import PiCommunicator

app = Flask(__name__)
CORS(app)

# Global state
tracker = FaceTracker()
communicator = PiCommunicator(pi_ip='192.168.1.100')
cap = cv2.VideoCapture(0)

current_state = {
    'yaw': 0,
    'pitch': 0,
    'face_detected': False
}

def generate_frames():
    """Generate webcam frames with tracking overlay."""
    global current_state, tracker
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Face tracking (head pose)
        yaw, pitch, annotated_frame = tracker.process_frame(frame)
        
        if yaw is not None and pitch is not None:
            current_state['yaw'] = yaw
            current_state['pitch'] = pitch
            current_state['face_detected'] = True
            
            # Send to Pi
            communicator.send_orientation(yaw, pitch)
        else:
            current_state['face_detected'] = False
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/laptop_feed')
def laptop_feed():
    """Stream laptop webcam with tracking overlay."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/orientation')
def get_orientation():
    """Get current orientation data."""
    return jsonify(current_state)

if __name__ == '__main__':
    print("Using FACE tracking (head pose)")
    print(f"\nLaptop tracker running on http://localhost:5002")
    print(f"Webcam feed: http://localhost:5002/laptop_feed")
    print(f"Orientation API: http://localhost:5002/orientation")
    
    app.run(host='0.0.0.0', port=5002, threaded=True)
