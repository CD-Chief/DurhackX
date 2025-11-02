# laptop/main.py
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
import threading
import argparse

print("=" * 50)
print("STARTING LAPTOP TRACKER...")
print("=" * 50)

# Import both trackers
from face_tracker import FaceTracker
from eye_tracker import EyeTracker
from communication import PiCommunicator

app = Flask(__name__)
CORS(app)

# Global state
tracker = None
tracker_type = "face"  # "face" or "eye"
communicator = PiCommunicator(pi_ip='192.168.1.100')
cap = cv2.VideoCapture(0)

current_state = {
    'yaw': 0,
    'pitch': 0,
    'face_detected': False,
    'tracker_type': 'face',
    'calibrated': False
}

def generate_frames():
    """Generate webcam frames with tracking overlay."""
    global current_state, tracker
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        
        if tracker_type == "face":
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
                
        else:  # eye tracking
            # Eye tracking (pupil gaze)
            yaw, is_blinking, annotated_frame = tracker.process_frame(frame)
            
            current_state['yaw'] = yaw
            current_state['pitch'] = 0  # Eye tracker only does horizontal
            current_state['face_detected'] = True
            current_state['calibrated'] = tracker.calibrated
            
            # Send to Pi
            if tracker.calibrated:
                communicator.send_orientation(yaw, 0)
        
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

@app.route('/calibrate', methods=['POST'])
def start_calibration():
    """Start calibration (eye tracker only)."""
    if tracker_type == "eye":
        tracker.start_calibration()
        return jsonify({'status': 'calibration_started'})
    return jsonify({'status': 'not_available', 'message': 'Only eye tracker supports calibration'})

@app.route('/switch_tracker', methods=['POST'])
def switch_tracker():
    """Switch between face and eye tracking."""
    global tracker, tracker_type
    
    data = request.json
    new_type = data.get('type', 'face')
    
    if new_type not in ['face', 'eye']:
        return jsonify({'error': 'Invalid tracker type'}), 400
    
    tracker_type = new_type
    current_state['tracker_type'] = tracker_type
    
    # Reinitialize tracker
    if tracker_type == "face":
        tracker = FaceTracker()
        print("Switched to FACE tracking")
    else:
        tracker = EyeTracker()
        print("Switched to EYE tracking")
    
    return jsonify({'status': 'switched', 'tracker_type': tracker_type})

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--tracker', choices=['face', 'eye'], default='face',
                       help='Tracking mode: face (head pose) or eye (pupil gaze)')
    args = parser.parse_args()
    
    tracker_type = args.tracker
    current_state['tracker_type'] = tracker_type
    
    # Initialize tracker
    if tracker_type == "face":
        tracker = FaceTracker()
        print("Using FACE tracking (head pose)")
    else:
        tracker = EyeTracker()
        print("Using EYE tracking (pupil gaze)")
        print("Press 'c' in the video window to calibrate")
    
    print(f"\nLaptop tracker running on http://localhost:5002")
    print(f"Webcam feed: http://localhost:5002/laptop_feed")
    print(f"Orientation API: http://localhost:5002/orientation")
    
    app.run(host='0.0.0.0', port=5002, threaded=True)
