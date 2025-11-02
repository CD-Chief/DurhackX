import requests
import json
import time

class PiCommunicator:
    def __init__(self, pi_ip='10.232.170.146', pi_port=5000):
        self.pi_url = f"http://{pi_ip}:{pi_port}/orientation"
        self.pi_ip = pi_ip
        self.pi_port = pi_port
        
        # Throttling and smoothing
        self.last_send_time = 0
        self.send_interval = 0.5  # Send every 500ms (2 Hz) - Slow but responsive
        self.last_yaw = 0
        self.last_pitch = 0
        self.smoothing_factor = 0.3  # Balanced: smooth but responsive
        
        print(f"PiCommunicator initialized: {self.pi_url}")
    
    def send_orientation(self, yaw, pitch):
        """Send orientation to Raspberry Pi with smoothing and throttling"""
        # Throttle: Only send every send_interval seconds
        current_time = time.time()
        if current_time - self.last_send_time < self.send_interval:
            return True
        
        try:
            # Smooth the values (exponential moving average)
            smoothed_yaw = self.last_yaw + self.smoothing_factor * (yaw - self.last_yaw)
            smoothed_pitch = self.last_pitch + self.smoothing_factor * (pitch - self.last_pitch)
            
            self.last_yaw = smoothed_yaw
            self.last_pitch = smoothed_pitch
            
            payload = {
                'yaw': float(smoothed_yaw),
                'pitch': float(smoothed_pitch)
            }
            
            # DEBUG: Print what we're sending
            print(f"[LAPTOP] Sending to Pi: yaw={payload['yaw']:.2f}°, pitch={payload['pitch']:.2f}°")
            
            response = requests.post(self.pi_url, json=payload, timeout=0.5)
            
            if response.status_code == 200:
                self.last_send_time = current_time
                result = response.json()
                print(f"[LAPTOP] Pi responded: servo_angle={result.get('servo_angle')}°")
            
            return response.status_code == 200
        except requests.exceptions.Timeout:
            print("\n[LAPTOP] Timeout connecting to Pi")
            return False
        except requests.exceptions.ConnectionError:
            print("\n[LAPTOP] Cannot connect to Pi")
            return False
        except Exception as e:
            print(f"\n[LAPTOP] Communication error: {e}")
            return False