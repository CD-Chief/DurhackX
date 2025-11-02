import requests
import json

class PiCommunicator:
    def __init__(self, pi_ip='10.232.170.146', pi_port=5000):
        self.pi_url = f"http://{pi_ip}:{pi_port}/orientation"
        self.pi_ip = pi_ip
        self.pi_port = pi_port
        print(f"PiCommunicator initialized: {self.pi_url}")
    
    def send_orientation(self, yaw, pitch):
        """Send orientation to Raspberry Pi"""
        try:
            payload = {
                'yaw': float(yaw) if yaw is not None else 0.0,
                'pitch': float(pitch) if pitch is not None else 0.0
            }
            
            # DEBUG: Print what we're sending
            print(f"[LAPTOP] Sending to Pi: yaw={payload['yaw']:.2f}°, pitch={payload['pitch']:.2f}°", end="\r")
            
            response = requests.post(self.pi_url, json=payload, timeout=0.1)
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n[LAPTOP] Pi responded: {result}")
            
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