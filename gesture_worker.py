import cv2
import mediapipe as mp
import math
import time
from pynput.keyboard import Key, Controller
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

class GestureWorker(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    gesture_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._is_running = True
        self.keyboard = Controller()
        
        # Cooldown management
        self.last_action_time = 0
        self.cooldown_duration = 0.5 # Default cooldown
    
    def calculate_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def is_finger_extended(self, landmarks, tip_id, pip_id, mcp_id):
        wrist = landmarks[0]
        tip = landmarks[tip_id]
        pip = landmarks[pip_id]
        return self.calculate_distance(tip, wrist) > self.calculate_distance(pip, wrist)

    def is_thumb_up(self, landmarks):
        thumb_tip = landmarks[4]
        thumb_mcp = landmarks[2]
        return thumb_tip.y < thumb_mcp.y - 0.05

    def detect_gesture(self, landmarks):
        # Finger statuses
        index_up = self.is_finger_extended(landmarks, 8, 6, 5)
        middle_up = self.is_finger_extended(landmarks, 12, 10, 9)
        ring_up = self.is_finger_extended(landmarks, 16, 14, 13)
        pinky_up = self.is_finger_extended(landmarks, 20, 18, 17)
        thumb_up_state = self.is_thumb_up(landmarks)

        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        thumb_index_dist = self.calculate_distance(thumb_tip, index_tip)

        # Logic
        if index_up and middle_up and ring_up and pinky_up and thumb_up_state:
            return "Open Palm", (0, 255, 0) # Green
        
        if not index_up and not middle_up and not ring_up and not pinky_up and not thumb_up_state:
            return "Thumbs Down", (255, 0, 0) # Red
        
        if thumb_up_state and not index_up and not middle_up and not ring_up and not pinky_up:
            return "Thumbs Up", (255, 255, 0) # Yellow
        
        if thumb_index_dist < 0.05 and middle_up and ring_up and pinky_up:
            return "OK", (255, 0, 255) # Magenta
        
        if index_up and middle_up and not ring_up and not pinky_up and not thumb_up_state:
            return "Peace", (255, 128, 0) # Orange
        
        return "Unknown", (128, 128, 128)

    def execute_action(self, gesture):
        """Executes keyboard action with non-blocking cooldown"""
        current_time = time.time()
        
        # Define cooldowns per gesture (seconds)
        cooldowns = {
            "Thumbs Up": 0.3,
            "Thumbs Down": 0.3,
            "OK": 1.5,     # Longer cooldown for Play/Pause to prevent toggle spam
            "Peace": 1.5   # Longer cooldown for Skip
        }

        if gesture not in cooldowns:
            return

        required_wait = cooldowns.get(gesture, 0.5)

        if (current_time - self.last_action_time) > required_wait:
            if gesture == "Thumbs Up":
                self.keyboard.press(Key.media_volume_up)
                self.keyboard.release(Key.media_volume_up)
            elif gesture == "Thumbs Down":
                self.keyboard.press(Key.media_volume_down)
                self.keyboard.release(Key.media_volume_down)
            elif gesture == "OK":
                self.keyboard.press(Key.media_play_pause)
                self.keyboard.release(Key.media_play_pause)
            elif gesture == "Peace":
                self.keyboard.press(Key.media_next)
                self.keyboard.release(Key.media_next)
            
            self.last_action_time = current_time

    def run(self):
        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils
        
        # Optimization: Define DrawingSpecs once, not every frame
        joint_spec = mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3)
        conn_spec = mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
        
        hands = mp_hands.Hands(
            max_num_hands=1, 
            min_detection_confidence=0.7, 
            min_tracking_confidence=0.7
        )
        
        cap = cv2.VideoCapture(0)
        
        while self._is_running:
            success, img = cap.read()
            if not success:
                continue

            # 1. Flip
            img = cv2.flip(img, 1)
            
            # 2. Convert to RGB ONCE for both MediaPipe and PyQt
            # Note: OpenCV uses BGR, MediaPipe/Qt use RGB.
            # We will work entirely in RGB after this point.
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            result = hands.process(img_rgb)
            
            gesture_text = ""
            color = (255, 255, 255)

            if result.multi_hand_landmarks:
                for hand_lms in result.multi_hand_landmarks:
                    # Draw directly on the RGB image
                    mp_draw.draw_landmarks(img_rgb, hand_lms, mp_hands.HAND_CONNECTIONS, joint_spec, conn_spec)
                    
                    gesture_text, color = self.detect_gesture(hand_lms.landmark)
                    
                    # Execute Action (Non-blocking)
                    self.execute_action(gesture_text)

            # Signal Gesture Text
            self.gesture_signal.emit(gesture_text if gesture_text else "No Hand")

            # Draw Text on Image (Use RGB colors)
            if gesture_text:
                cv2.putText(img_rgb, gesture_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            # 3. Create QImage directly from the modified RGB image
            h, w, ch = img_rgb.shape
            bytes_per_line = ch * w
            convert_to_qt_format = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            self.change_pixmap_signal.emit(convert_to_qt_format)
            
            # Tiny sleep to yield execution to GUI thread
            self.msleep(10) 

        cap.release()

    def stop(self):
        self._is_running = False
        self.wait()