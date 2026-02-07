import cv2
import mediapipe as mp
import math
import time
from pynput.keyboard import Key, Controller

keyboard = Controller()

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)

def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two landmarks"""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def is_finger_extended(landmarks, tip_id, pip_id, mcp_id):
    """Check if a finger is extended based on landmarks"""
    # Finger is extended if tip is farther from wrist than PIP joint
    wrist = landmarks[0]
    tip = landmarks[tip_id]
    pip = landmarks[pip_id]
    
    tip_dist = calculate_distance(tip, wrist)
    pip_dist = calculate_distance(pip, wrist)
    
    return tip_dist > pip_dist

def is_thumb_up(landmarks, handedness):
    """Check if thumb is pointing up"""
    thumb_tip = landmarks[4]
    thumb_mcp = landmarks[2]
    wrist = landmarks[0]
    
    # Thumb is up if tip is significantly above MCP joint
    is_up = thumb_tip.y < thumb_mcp.y - 0.05
    
    return is_up

def is_thumb_down(landmarks, handedness):
    """Check if thumb is pointing down"""
    thumb_tip = landmarks[4]
    thumb_mcp = landmarks[2]
    
    # Thumb is down if tip is significantly below MCP joint
    is_down = thumb_tip.y > thumb_mcp.y + 0.05
    
    return is_down

def detect_gesture(landmarks, handedness):
    """
    Detect gestures: Thumbs Up, Thumbs Down, OK Sign, Peace Sign, Open Palm, Closed Palm
    """
    # Define finger landmarks
    # Index: tip=8, pip=6, mcp=5
    # Middle: tip=12, pip=10, mcp=9
    # Ring: tip=16, pip=14, mcp=13
    # Pinky: tip=20, pip=18, mcp=17
    
    # Check which fingers are extended
    index_up = is_finger_extended(landmarks, 8, 6, 5)
    middle_up = is_finger_extended(landmarks, 12, 10, 9)
    ring_up = is_finger_extended(landmarks, 16, 14, 13)
    pinky_up = is_finger_extended(landmarks, 20, 18, 17)
    thumb_extended = is_thumb_up(landmarks, handedness)
    
    # Calculate distances for OK sign detection
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    thumb_index_dist = calculate_distance(thumb_tip, index_tip)
    
    # 1. OPEN PALM - All fingers extended
    if index_up and middle_up and ring_up and pinky_up and thumb_extended:
        return "open palm", (0, 255, 0)
    
    # 2. CLOSED FIST - No fingers extended
    if not index_up and not middle_up and not ring_up and not pinky_up and not thumb_extended:
        return "thumbs down", (0, 0, 255)
    
    # 3. THUMBS UP - Only thumb up, other fingers closed
    if is_thumb_up(landmarks, handedness) and not index_up and not middle_up and not ring_up and not pinky_up:
        return "thumbs up", (255, 255, 0)
    
    # 5. OK SIGN - Thumb and index touching, other fingers extended
    if thumb_index_dist < 0.05 and middle_up and ring_up and pinky_up:
        return "ok", (255, 0, 255)
    
    # 6. PEACE SIGN - Index and middle up, others down
    if index_up and middle_up and not ring_up and not pinky_up and not thumb_extended:
        return "peace", (255, 128, 0)
    
    return "Unknown Gesture", (128, 128, 128)

#music control function
def play_pause():
    keyboard.press(Key.media_play_pause)
    keyboard.release(Key.media_play_pause)

def next_track():
    keyboard.press(Key.media_next)
    keyboard.release(Key.media_next)

def previous_track():
    keyboard.press(Key.media_previous)
    keyboard.release(Key.media_previous)

def volume_up():
    keyboard.press(Key.media_volume_up)
    keyboard.release(Key.media_volume_up)

def volume_down():
    keyboard.press(Key.media_volume_down)
    keyboard.release(Key.media_volume_down)


# Main loop
print("Hand Gesture Recognition Started!")
print("Gestures: Thumbs Up, Thumbs Down, OK Sign, Peace Sign, Open Palm, Closed Fist")
print("Press 'q' to quit")

while True:
    success, img = cap.read()
    if not success:
        print("Failed to read from camera")
        break
    
    # Flip image for selfie view
    img = cv2.flip(img, 1)
    
    # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)
    
    gesture_text = "No Hand Detected"
    color = (255, 255, 255)
    
    if result.multi_hand_landmarks and result.multi_handedness:
        for hand_lms, hand_info in zip(result.multi_hand_landmarks, result.multi_handedness):
            # Draw hand landmarks
            mp_draw.draw_landmarks(
                img, hand_lms, mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
            )
            
            # Get handedness
            handedness = hand_info.classification[0].label
            
            # Detect gesture
            gesture_text, color = detect_gesture(hand_lms.landmark, handedness)
    
    #gesture control mapping
    if gesture_text == "thumbs up":
        volume_up()
        time.sleep(0.5)
    elif gesture_text == "thumbs down":
        volume_down()
        time.sleep(0.5)
    elif gesture_text == "ok":
        play_pause()
        time.sleep(1) 
    elif gesture_text == "peace":
        next_track()
        time.sleep(1) 

    # Create background rectangle for text
    cv2.rectangle(img, (10, 10), (650, 80), (0, 0, 0), -1)
    
    # Display gesture text
    cv2.putText(
        img, gesture_text, (20, 55),
        cv2.FONT_HERSHEY_SIMPLEX, 1.5,
        color, 3
    )
    
    # Add instructions at bottom
    cv2.putText(
        img, "Press 'q' to quit", (20, img.shape[0] - 50),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
        (255, 255, 255), 2
    )

    cv2.putText(
        img, "Gestures: Thumbs Up, Thumbs Down, OK Sign, Peace Sign, Open Palm, Closed Fist", (20, img.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
        (255, 255, 255), 1
    )
    
    cv2.imshow("Hand Gesture Recognition", img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Program ended")