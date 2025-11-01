import RPi.GPIO as GPIO
import time

# Set up GPIO pin
SERVO_PIN = 2  # GPIO2 (Physical Pin 3) - change to 18 for GPIO18/Pin 12 if needed
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Create PWM instance at 50Hz
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def set_angle(angle):
    """Move servo to specified angle (0-180)"""
    duty_cycle = (angle / 18) + 2.5
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

try:
    print("Testing servo motor...")
    print("Moving to 0 degrees")
    set_angle(0)
    time.sleep(1)
    
    print("Moving to 90 degrees")
    set_angle(90)
    time.sleep(1)
    
    print("Moving to 180 degrees")
    set_angle(180)
    time.sleep(1)
    
    print("Back to 90 degrees")
    set_angle(90)

    
except KeyboardInterrupt:
    print("\nExiting...")

finally:
    pwm.stop()
    GPIO.cleanup()