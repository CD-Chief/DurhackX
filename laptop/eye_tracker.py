# laptop/eye_tracker.py
import cv2
import mediapipe as mp
import numpy as np
from collections import deque

class EyeTracker:
    def __init__(self, model_path='models/face_landmarker_v2_with_blendshapes.task'):
        """
        Eye/pupil tracker using MediaPipe Face Landmarker.
        Returns horizontal gaze direction (yaw) for servo control.
        """
        # MediaPipe setup
        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1
        )
        self.detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        
        # Eye landmarks (from your teammate's code)
        self.LEFT_EYE_INNER = 133
        self.LEFT_EYE_OUTER = 33
        self.LEFT_EYE_TOP = 159
        self.LEFT_EYE_BOTTOM = 145
        self.RIGHT_EYE_INNER = 362
        self.RIGHT_EYE_OUTER = 263
        self.RIGHT_EYE_TOP = 386
        self.RIGHT_EYE_BOTTOM = 374
        self.LEFT_IRIS = [468, 469, 470, 471, 472]
        self.RIGHT_IRIS = [473, 474, 475, 476, 477]
        
        # Calibration points (3-point horizontal)
        self.calibration_points = [
            -30.0,  # Left (degrees)
            0.0,    # Center
            30.0    # Right
        ]
        self.calibration_index = 0
        self.calibration_data = []  # [(pupil_x, target_angle), ...]
        self.calibrating = False
        self.hold_frames = 0
        self.frames_per_point = 30  # ~1 sec at 30 FPS
        
        # Mapping parameters
        self.scale = 1.0
        self.offset = 0.0
        self.calibrated = False
        
        # Smoothing
        self.yaw_buffer = deque(maxlen=5)
        
        # Blink detection
        self.blink_threshold = 0.4

    def get_pupil_position(self, face_landmarks):
        """Return normalized horizontal pupil position (0-1)."""
        def get_eye_rel_x(eye_def, iris_indices):
            inner = face_landmarks[eye_def['inner']]
            outer = face_landmarks[eye_def['outer']]
            
            eye_w = abs(outer.x - inner.x)
            iris_x = np.mean([face_landmarks[i].x for i in iris_indices])
            
            # Relative within eye (0 = inner, 1 = outer)
            rel_x = (iris_x - min(inner.x, outer.x)) / (eye_w + 1e-6)
            return rel_x

        left_eye = {
            'inner': self.LEFT_EYE_INNER,
            'outer': self.LEFT_EYE_OUTER,
            'top': self.LEFT_EYE_TOP,
            'bottom': self.LEFT_EYE_BOTTOM
        }
        right_eye = {
            'inner': self.RIGHT_EYE_INNER,
            'outer': self.RIGHT_EYE_OUTER,
            'top': self.RIGHT_EYE_TOP,
            'bottom': self.RIGHT_EYE_BOTTOM
        }
        
        lx = get_eye_rel_x(left_eye, self.LEFT_IRIS)
        rx = get_eye_rel_x(right_eye, self.RIGHT_IRIS)
        
        avg_x = (lx + rx) / 2.0
        return avg_x  # 0-1, where 0.5 is center

    def start_calibration(self):
        """Start 3-point calibration."""
        print("Starting 3-point eye calibration (Left/Center/Right)...")
        self.calibration_data = []
        self.calibration_index = 0
        self.calibrating = True
        self.hold_frames = 0

    def run_calibration_step(self, frame, pupil_x):
        """Run one step of calibration."""
        if self.calibration_index >= len(self.calibration_points):
            self.finish_calibration()
            return frame

        target_angle = self.calibration_points[self.calibration_index]
        
        # Visual feedback
        h, w = frame.shape[:2]
        direction = ["LEFT", "CENTER", "RIGHT"][self.calibration_index]
        cv2.putText(frame, f"Look {direction} ({self.calibration_index + 1}/3)", 
                   (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Hold position...", 
                   (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Draw arrow indicator
        arrow_x = w // 2
        if self.calibration_index == 0:  # Left
            cv2.arrowedLine(frame, (w//2, h//2), (100, h//2), (0, 255, 0), 5)
        elif self.calibration_index == 1:  # Center
            cv2.circle(frame, (w//2, h//2), 30, (0, 255, 0), 5)
        else:  # Right
            cv2.arrowedLine(frame, (w//2, h//2), (w-100, h//2), (0, 255, 0), 5)

        # Hold and collect
        self.hold_frames += 1
        if self.hold_frames >= self.frames_per_point:
            self.calibration_data.append((pupil_x, target_angle))
            print(f"✓ Captured point {self.calibration_index + 1}/3: pupil={pupil_x:.3f} → {target_angle}°")
            self.calibration_index += 1
            self.hold_frames = 0

        return frame

    def finish_calibration(self):
        """Compute linear mapping from pupil position to servo angle."""
        if len(self.calibration_data) < 2:
            print("❌ Not enough calibration data!")
            self.calibrated = False
            self.calibrating = False
            return

        pupil_x = np.array([d[0] for d in self.calibration_data])
        target_angle = np.array([d[1] for d in self.calibration_data])

        # Linear fit: angle = scale * pupil_x + offset
        A = np.vstack([pupil_x, np.ones(len(pupil_x))]).T
        self.scale, self.offset = np.linalg.lstsq(A, target_angle, rcond=None)[0]

        self.calibrated = True
        self.calibrating = False
        print(f"✅ Calibration complete!")
        print(f"   Mapping: yaw = {self.scale:.2f} * pupil + {self.offset:.2f}")

    def map_gaze_to_yaw(self, pupil_x):
        """Convert pupil position to servo yaw angle."""
        if not self.calibrated:
            return 0.0  # Default center
        
        yaw = self.scale * pupil_x + self.offset
        
        # Clamp to reasonable servo range
        yaw = np.clip(yaw, -45, 45)
        
        # Smooth
        self.yaw_buffer.append(yaw)
        smooth_yaw = np.mean(self.yaw_buffer)
        
        return smooth_yaw

    def detect_blink(self, blendshapes):
        """Detect if both eyes are blinking."""
        if not blendshapes:
            return False
        
        left = right = 0
        for b in blendshapes:
            if b.category_name == 'eyeBlinkLeft':
                left = b.score
            elif b.category_name == 'eyeBlinkRight':
                right = b.score
        
        return left > self.blink_threshold and right > self.blink_threshold

    def process_frame(self, frame):
        """
        Process frame and return yaw angle, blink status, and annotated frame.
        Returns: (yaw, is_blinking, annotated_frame)
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self.detector.detect(mp_image)

        pupil_x = 0.5  # Default center
        yaw = 0.0
        is_blinking = False

        if result.face_landmarks:
            pupil_x = self.get_pupil_position(result.face_landmarks[0])
            
            # Draw pupil indicator
            h, w = frame.shape[:2]
            px = int(pupil_x * w)
            py = h // 2
            cv2.circle(frame, (px, py), 10, (255, 0, 0), -1)
            
            if result.face_blendshapes:
                is_blinking = self.detect_blink(result.face_blendshapes[0])

        # Handle calibration
        if self.calibrating:
            frame = self.run_calibration_step(frame, pupil_x)
        else:
            if self.calibrated:
                yaw = self.map_gaze_to_yaw(pupil_x)
                
                # Status overlay
                status = f"Yaw: {yaw:.1f}° {'[BLINK]' if is_blinking else ''}"
                cv2.putText(frame, status, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Press 'c' to calibrate", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        return yaw, is_blinking, frame
