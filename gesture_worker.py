import cv2
import mediapipe as mp
import time
from pynput.keyboard import Key, Controller
from PyQt6.QtCore import QThread, pyqtSignal, Qt
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
        # Optimization: Map gestures to Keys directly for faster lookup
        self.key_map = {
            "Thumbs Up": (Key.media_volume_up, 0.3),
            "Thumbs Down": (Key.media_volume_down, 0.3),
            "OK": (Key.media_play_pause, 1.5),
            "Peace": (Key.media_next, 1.5)
        }

    # OPTIMIZATION: Use Squared Euclidean Distance
    # Removing math.sqrt() saves CPU cycles on every frame
    def get_dist_sq(self, p1, p2):
        return (p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2

    def is_finger_extended(self, landmarks, tip_id, pip_id):
        # We only need to know if the TIP is further from wrist than the PIP
        wrist = landmarks[0]
        tip = landmarks[tip_id]
        pip = landmarks[pip_id]
        
        return self.get_dist_sq(tip, wrist) > self.get_dist_sq(pip, wrist)

    def is_thumb_up(self, landmarks):
        # Simple Y-check: Tip above knuckle (Remember: Y decreases going UP in images)
        return landmarks[4].y < landmarks[2].y - 0.05

    def detect_gesture(self, lm):
        # lm = landmarks list
        
        # Check fingers (Indices: 8=Index, 12=Middle, 16=Ring, 20=Pinky)
        # We compare Tip vs PIP (Knuckle)
        index_up = self.is_finger_extended(lm, 8, 6)
        middle_up = self.is_finger_extended(lm, 12, 10)
        ring_up = self.is_finger_extended(lm, 16, 14)
        pinky_up = self.is_finger_extended(lm, 20, 18)
        
        thumb_up = self.is_thumb_up(lm)

        # Optimization: Calculate this only once
        thumb_index_dist = self.get_dist_sq(lm[4], lm[8])

        # Logic Tree
        # 1. Open Palm (All Up)
        if index_up and middle_up and ring_up and pinky_up and thumb_up:
            return "Open Palm", (0, 255, 0) # Green
        
        # 2. Thumbs Down (All Down, Thumb not up) - You might want to add specific thumb down logic here
        # Currently this checks "Fist" effectively
        if not index_up and not middle_up and not ring_up and not pinky_up and not thumb_up:
            return "Thumbs Down", (255, 0, 0) # Red
        
        # 3. Thumbs Up (Fist + Thumb Up)
        if thumb_up and not index_up and not middle_up and not ring_up and not pinky_up:
            return "Thumbs Up", (255, 255, 0) # Yellow
        
        # 4. OK Sign (Thumb touches Index, others up)
        # 0.0025 is 0.05 squared
        if thumb_index_dist < 0.0025 and middle_up and ring_up and pinky_up:
            return "OK", (255, 0, 255) # Magenta
        
        # 5. Peace Sign (Index & Middle Up)
        if index_up and middle_up and not ring_up and not pinky_up:
            return "Peace", (255, 128, 0) # Orange
        
        return None, (128, 128, 128)

    def execute_action(self, gesture):
        if not gesture or gesture not in self.key_map:
            return

        key, cooldown = self.key_map[gesture]
        current_time = time.time()

        if (current_time - self.last_action_time) > cooldown:
            self.keyboard.press(key)
            self.keyboard.release(key)
            self.last_action_time = current_time

    def run(self):
        # OPTIMIZATION: Initialize MediaPipe options outside the loop
        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils
        
        # Pre-define drawing specs so we don't recreate them 60 times a second
        joint_spec = mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3)
        conn_spec = mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
        
        # OPTIMIZATION: model_complexity=0 is the "Lite" model (Faster, slightly less accurate)
        # perfect for real-time gesture control on laptops.
        with mp_hands.Hands(
            max_num_hands=1,
            model_complexity=0, 
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        ) as hands:
            
            cap = cv2.VideoCapture(0)
            # Reduce resolution for speed if needed (Optional)
            # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            while self._is_running:
                success, img = cap.read()
                if not success:
                    self.msleep(100)
                    continue

                # 1. Flip
                img = cv2.flip(img, 1)
                
                # 2. Color Conversion
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # OPTIMIZATION: Pass by reference, flag as not writeable
                # This drastically speeds up the internal MediaPipe processing
                img_rgb.flags.writeable = False
                result = hands.process(img_rgb)
                img_rgb.flags.writeable = True # Unlock for drawing
                
                gesture_text = "No Hand"
                color = (100, 100, 100)

                if result.multi_hand_landmarks:
                    for hand_lms in result.multi_hand_landmarks:
                        # Draw landmarks
                        mp_draw.draw_landmarks(img_rgb, hand_lms, mp_hands.HAND_CONNECTIONS, joint_spec, conn_spec)
                        
                        # Detect
                        detected_gesture, detected_color = self.detect_gesture(hand_lms.landmark)
                        
                        if detected_gesture:
                            gesture_text = detected_gesture
                            color = detected_color
                            self.execute_action(gesture_text)

                # Emit Text Signal
                self.gesture_signal.emit(gesture_text)

                # Draw Text (On RGB image directly)
                # Using a shadow (black) + text (color) for better visibility
                cv2.putText(img_rgb, gesture_text, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 4)
                cv2.putText(img_rgb, gesture_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                # 3. Create QImage
                h, w, ch = img_rgb.shape
                bytes_per_line = ch * w
                
                # OPTIMIZATION: .copy() prevents memory issues when passing to GUI thread
                qt_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                
                self.change_pixmap_signal.emit(qt_img)
                
                # Yield to GUI
                self.msleep(10) 

            cap.release()

    def stop(self):
        self._is_running = False
        self.wait()