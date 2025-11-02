# laptop/face_tracker.py
import cv2
import mediapipe as mp
import numpy as np
from collections import deque

class FaceTracker:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Smoothing
        self.yaw_buffer = deque(maxlen=5)
        self.pitch_buffer = deque(maxlen=5)
        
    def get_head_pose(self, face_landmarks, img_shape):
        """Calculate yaw and pitch from face landmarks"""
        h, w = img_shape[:2]
        
        # 3D model points
        face_3d = []
        face_2d = []
        
        # Key landmarks
        for idx in [1, 33, 263, 61, 291, 199]:
            lm = face_landmarks.landmark[idx]
            x, y = int(lm.x * w), int(lm.y * h)
            face_2d.append([x, y])
            face_3d.append([x, y, lm.z])
        
        face_2d = np.array(face_2d, dtype=np.float64)
        face_3d = np.array(face_3d, dtype=np.float64)
        
        # Camera matrix
        focal_length = w
        cam_matrix = np.array([
            [focal_length, 0, w / 2],
            [0, focal_length, h / 2],
            [0, 0, 1]
        ])
        
        dist_matrix = np.zeros((4, 1), dtype=np.float64)
        
        # Solve PnP
        success, rot_vec, trans_vec = cv2.solvePnP(
            face_3d, face_2d, cam_matrix, dist_matrix
        )
        
        # Get rotation matrix
        rmat, _ = cv2.Rodrigues(rot_vec)
        
        # Calculate angles
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        
        yaw = angles[1] * 360
        pitch = angles[0] * 360
        
        return yaw, pitch
    
    def process_frame(self, frame):
        """
        Process frame and return yaw, pitch, and annotated frame.
        Returns: (yaw, pitch, annotated_frame)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        yaw, pitch = None, None
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            yaw, pitch = self.get_head_pose(face_landmarks, frame.shape)
            
            # Smooth values
            self.yaw_buffer.append(yaw)
            self.pitch_buffer.append(pitch)
            
            yaw = np.mean(self.yaw_buffer)
            pitch = np.mean(self.pitch_buffer)
            
            # Draw landmarks
            self.mp_drawing.draw_landmarks(
                image=frame,
                landmark_list=face_landmarks,
                connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing_styles
                .get_default_face_mesh_tesselation_style()
            )
            
            # Add text overlay
            cv2.putText(frame, f"Yaw: {yaw:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Pitch: {pitch:.1f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "No face detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        return yaw, pitch, frame
