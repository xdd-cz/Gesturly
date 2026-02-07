import cv2
import mediapipe as mp
import math
import time
from pynput.keyboard import Key, Controller
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage

class GestureWorker(QThread):
    # Signal to send the video frame to the GUI
    change_pixmap_signal = pyqtSignal(QImage)
    
    def __init__(self):
        super().__init__()
        self._is_running = True
        self.keyboard = Controller()

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

    def detect_gesture(self, landmarks, handedness):
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
            return "open palm", (0, 255, 0)
        
        if not index_up and not middle_up and not ring_up and not pinky_up and not thumb_up_state:
            return "thumbs down", (0, 0, 255)
        
        if thumb_up_state and not index_up and not middle_up and not ring_up and not pinky_up:
            return "thumbs up", (255, 255, 0)
        
        if thumb_index_dist < 0.05 and middle_up and ring_up and pinky_up:
            return "ok", (255, 0, 255)
        
        if index_up and middle_up and not ring_up and not pinky_up and not thumb_up_state:
            return "peace", (255, 128, 0)
        
        return "Unknown", (128, 128, 128)

    def run(self):
        # Setup MediaPipe
        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils
        hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        
        cap = cv2.VideoCapture(0)
        
        while self._is_running:
            success, img = cap.read()
            if not success:
                continue

            img = cv2.flip(img, 1)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)
            
            gesture_text = ""
            color = (255, 255, 255)

            if result.multi_hand_landmarks:
                for hand_lms, hand_info in zip(result.multi_hand_landmarks, result.multi_handedness):
                    mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS, mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3), mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2))
                    handedness = hand_info.classification[0].label
                    gesture_text, color = self.detect_gesture(hand_lms.landmark, handedness)

            # --- Control Logic ---
            if gesture_text == "thumbs up":
                self.keyboard.press(Key.media_volume_up)
                self.keyboard.release(Key.media_volume_up)
                time.sleep(0.2) # Reduced sleep for smoother UI
            elif gesture_text == "thumbs down":
                self.keyboard.press(Key.media_volume_down)
                self.keyboard.release(Key.media_volume_down)
                time.sleep(0.2)
            elif gesture_text == "ok":
                self.keyboard.press(Key.media_play_pause)
                self.keyboard.release(Key.media_play_pause)
                time.sleep(1)
            elif gesture_text == "peace":
                self.keyboard.press(Key.media_next)
                self.keyboard.release(Key.media_next)
                time.sleep(1)

            # --- UI Preparation ---
            # Add text to image before sending to GUI
            if gesture_text:
                cv2.putText(img, gesture_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            # Convert to QImage for PyQt
            h, w, ch = img.shape
            bytes_per_line = ch * w
            
            final_display_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # The image must be RGB for PyQt
            convert_to_qt_format = QImage(final_display_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Emit the signal
            self.change_pixmap_signal.emit(convert_to_qt_format)
            
            # Small sleep to save CPU
            time.sleep(0.01)

        cap.release()

    def stop(self):
        self._is_running = False
        self.wait()