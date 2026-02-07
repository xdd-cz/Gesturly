import sys
import subprocess
import os
import tempfile
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QFrame, QStackedWidget, QGridLayout, QSlider, QComboBox, QCheckBox, QSizePolicy, QGraphicsBlurEffect, QGraphicsDropShadowEffect
)

from PyQt6.QtGui import QFontDatabase, QFont, QPixmap, QCursor, QImage, QColor, QPainter, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from gesture_worker import GestureWorker

# --- Effects ----


class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class AspectLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pixmap = None

    def setPixmap(self, p):
        self._pixmap = p
        self._update_display()

    def resizeEvent(self, event):
        self._update_display()
        super().resizeEvent(event)

    def _update_display(self):
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled)
            
    def sizeHint(self):
        return self.size()

# --- HOME PAGE ---

class HomePage(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.current_song_id = None
        
        # Main Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        nabla = "Six Caps"
        urbanist = "Urbanist"

        # --- LEFT COLUMN (Camera) ---
        intro = QFrame()
        intro.setStyleSheet("background-color: #28332E;")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(20, 20, 20, 20)
        
        home_title = QLabel("HOME")
        home_title.setFont(QFont(nabla, 60))
        home_title.setStyleSheet("color: #F7FFE3;")
        intro_layout.addWidget(home_title)
        
        body = QLabel("Welcome to gesturly. Start controlling your music<br> with simple hand gestures.")
        body.setFont(QFont(urbanist, 16))
        body.setWordWrap(True)
        intro_layout.addWidget(body)
        
        cam_title = QLabel("Camera feed")
        cam_title.setFont(QFont(nabla, 40))
        intro_layout.addWidget(cam_title)
        
        # Camera Feed
        self.feed_label = AspectLabel()
        self.feed_label.setText("Loading Camera...")
        self.feed_label.setStyleSheet("background-color: #000; border-radius: 10px;")
        self.feed_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        intro_layout.addWidget(self.feed_label)
        
        self.gesture_status = QLabel("State: No Hand")
        self.gesture_status.setFont(QFont(urbanist, 18, QFont.Weight.Bold))
        self.gesture_status.setStyleSheet("color: #F7FFE3; margin-top: 10px;")
        self.gesture_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(self.gesture_status)
        
        # --- RIGHT COLUMN  ---
        playing = QFrame()
        playing.setStyleSheet("background-color: #252F2A;")
        
        # VITAL: This policy tells the right column to NOT be greedy horizontally.
        # It will only take the width it *needs*.
        playing.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        
        playing_layout = QVBoxLayout(playing)
        playing_layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("Now Playing")
        title_label.setFont(QFont(nabla, 60))
        title_label.setStyleSheet("color: #F7FFE3;")
        playing_layout.addWidget(title_label)
        
        # Album Art
        self.album_art_label = AspectLabel()
        self.album_art_label.setText("🎵")
        self.album_art_label.setStyleSheet("background-color: #1a1a1a; border-radius: 10px;")
        
        # We give the art a minimum size so the column doesn't collapse too small
        self.album_art_label.setMinimumSize(250, 250)
        
        # It can expand, but the parent frame (playing) keeps it in check
        self.album_art_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        playing_layout.addWidget(self.album_art_label)
        
        self.song_title = QLabel("Not Playing")
        self.song_title.setFont(QFont(urbanist, 20, QFont.Weight.DemiBold))
        self.song_title.setStyleSheet("color: #F7FFE3;")
        self.song_title.setWordWrap(True)
        # Prevent long text from forcing the column wide
        self.song_title.setMaximumWidth(350) 
        playing_layout.addWidget(self.song_title)
        
        self.song_artist = QLabel("Play a song to start")
        self.song_artist.setFont(QFont(urbanist, 14))
        self.song_artist.setStyleSheet("color: #cccccc;")
        self.song_artist.setWordWrap(True)
        self.song_artist.setMaximumWidth(350)
        playing_layout.addWidget(self.song_artist)
        
        # --- THE MAGIC LAYOUT FIX ---
        # 1 = Left Column gets ALL extra space
        # 0 = Right Column gets NO extra space (only what it needs)
        layout.addWidget(intro, 1)
        layout.addWidget(playing, 0)

        # Signals
        self.worker.change_pixmap_signal.connect(self.update_video_feed)
        self.worker.gesture_signal.connect(self.update_gesture_label)

        # Timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_song_info)
        self.update_timer.start(2000)
        self.update_song_info()

    def update_video_feed(self, qt_image):
        self.feed_label.setPixmap(QPixmap.fromImage(qt_image))

    def update_gesture_label(self, gesture_text):
        self.gesture_status.setText(f"State: {gesture_text}")

    # --- Music Helpers ---
    def get_spotify_info(self):
        script = '''if application "Spotify" is running then
            tell application "Spotify"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|spotify"
                end if
            end tell
        end if
        return ""'''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=1)
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    return {'song': parts[0], 'artist': parts[1], 'source': 'spotify'}
        except: pass
        return None
    
    def get_music_info(self):
        script = '''if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|music"
                end if
            end tell
        end if
        return ""'''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=1)
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    return {'song': parts[0], 'artist': parts[1], 'source': 'music'}
        except: pass
        return None

    def get_album_art_from_music(self):
        temp_file = os.path.join(tempfile.gettempdir(), "gesturly_album_art.jpg")
        script = f'''
        if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    try
                        set artworkData to data of artwork 1 of current track
                        set fileRef to open for access POSIX file "{temp_file}" with write permission
                        set eof fileRef to 0
                        write artworkData to fileRef
                        close access fileRef
                        return "success"
                    on error
                        return "error"
                    end try
                end if
            end tell
        end if
        return "not_playing"
        '''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=2)
            if "success" in result.stdout:
                return QPixmap(temp_file)
        except: pass
        return None

    def update_song_info(self):
        song_info = self.get_spotify_info() or self.get_music_info()
        if song_info:
            song_id = f"{song_info['song']}|{song_info['artist']}"
            self.song_title.setText(song_info['song'])
            self.song_artist.setText(song_info['artist'])
            
            if song_id != self.current_song_id:
                self.current_song_id = song_id
                pixmap = None
                if song_info['source'] == 'music':
                    pixmap = self.get_album_art_from_music()
                
                if pixmap and not pixmap.isNull():
                    self.album_art_label.setPixmap(pixmap)
                    self.album_art_label.setText("") 
                else:
                    self.album_art_label.clear()
                    self.album_art_label.setText("🎵")
        else:
            self.current_song_id = None
            self.song_title.setText("Not Playing")
            self.song_artist.setText("Play Spotify or Apple Music")
            self.album_art_label.clear()
            self.album_art_label.setText("🎵")


# --- Settings Page ---

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 60, 60, 60)
        main_layout.setSpacing(40)
        
        # ------------------------------------------------
        # SECTION 1: TUTORIAL (HOW TO USE)
        # ------------------------------------------------
        title_tutorial = QLabel("GESTURE GUIDE")
        title_tutorial.setFont(QFont("Urbanist", 24, QFont.Weight.Bold))
        title_tutorial.setStyleSheet("color: #FFFFFF;")
        main_layout.addWidget(title_tutorial)

        # Grid for the tutorial cards
        tutorial_grid = QGridLayout()
        tutorial_grid.setSpacing(20)

        # Add cards (Icon/Text -> Action)
        # You can change the text to match your actual gestures!
        tutorial_grid.addWidget(self.create_tutorial_card("✋", "OPEN PALM", "Play / Pause Music"), 0, 0)
        tutorial_grid.addWidget(self.create_tutorial_card("☝️", "POINT UP", "Volume Up"), 0, 1)
        tutorial_grid.addWidget(self.create_tutorial_card("👇", "POINT DOWN", "Volume Down"), 1, 0)
        tutorial_grid.addWidget(self.create_tutorial_card("✊", "CLOSED FIST", "Mute Audio"), 1, 1)

        main_layout.addLayout(tutorial_grid)

        # Divider Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(255, 255, 255, 0.2);")
        main_layout.addWidget(line)

        # ------------------------------------------------
        # SECTION 2: APP PREFERENCES
        # ------------------------------------------------
        title_settings = QLabel("PREFERENCES")
        title_settings.setFont(QFont("Urbanist", 24, QFont.Weight.Bold))
        title_settings.setStyleSheet("color: #FFFFFF;")
        main_layout.addWidget(title_settings)

        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(30)

        # A) Camera Selection
        cam_layout = QVBoxLayout()
        cam_label = QLabel("Camera Input")
        cam_label.setFont(QFont("Urbanist", 16))
        cam_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        
        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["FaceTime HD Camera", "External Webcam", "OBS Virtual Camera"])
        self.cam_combo.setFont(QFont("Urbanist", 14))
        # Styling the dropdown to look modern
        self.cam_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #444;
            }
        """)
        
        cam_layout.addWidget(cam_label)
        cam_layout.addWidget(self.cam_combo)
        settings_layout.addLayout(cam_layout)

        # B) Sensitivity Slider
        sens_layout = QVBoxLayout()
        sens_header = QHBoxLayout()
        
        sens_label = QLabel("Gesture Sensitivity")
        sens_label.setFont(QFont("Urbanist", 16))
        sens_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        
        sens_value = QLabel("High") # Just a placeholder text
        sens_value.setFont(QFont("Urbanist", 16, QFont.Weight.Bold))
        sens_value.setStyleSheet("color: #F7FFE3;")
        
        sens_header.addWidget(sens_label)
        sens_header.addStretch()
        sens_header.addWidget(sens_value)
        
        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setRange(1, 100)
        self.sens_slider.setValue(80)
        self.sens_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #F7FFE3;
                width: 24px;
                margin: -8px 0;
                border-radius: 12px;
            }
        """)
        
        sens_layout.addLayout(sens_header)
        sens_layout.addWidget(self.sens_slider)
        settings_layout.addLayout(sens_layout)
        
        # C) Show Skeleton Toggle
        self.debug_check = QCheckBox("Show Hand Skeleton (Debug Mode)")
        self.debug_check.setFont(QFont("Urbanist", 16))
        self.debug_check.setStyleSheet("""
            QCheckBox { color: rgba(255, 255, 255, 0.9); spacing: 15px; }
            QCheckBox::indicator { width: 20px; height: 20px; border-radius: 5px; border: 1px solid #666; }
            QCheckBox::indicator:checked { background-color: #F7FFE3; border-color: #F7FFE3; }
        """)
        
        settings_layout.addWidget(self.debug_check)

        main_layout.addLayout(settings_layout)
        main_layout.addStretch() # Push everything to the top

    # --- HELPER TO MAKE CARDS ---
    def create_tutorial_card(self, icon, title, desc):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Icon (Emoji)
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 30)) # Use emoji font
        icon_label.setStyleSheet("background-color: transparent; border: none;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title (Gesture Name)
        title_label = QLabel(title)
        title_label.setFont(QFont("Urbanist", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #F7FFE3; background-color: transparent; border: none; letter-spacing: 2px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Description (Action)
        desc_label = QLabel(desc)
        desc_label.setFont(QFont("Urbanist", 12))
        desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); background-color: transparent; border: none;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        
        return card
        
# --- Big Picture Page ---

class BigPicturePage(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.current_song_id = None
        self.bg_pixmap = None 
        
        # 1. Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(60, 60, 60, 60)
        
        # ------------------------------------------------
        # TOP: Gesture
        # ------------------------------------------------
        self.gesture_label = QLabel("NO HAND")
        font = QFont("Urbanist", 14, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        self.gesture_label.setFont(font)
        # Transparent background, white text
        self.gesture_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background-color: transparent;")
        self.main_layout.addWidget(self.gesture_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.main_layout.addStretch(1)
        
        # ------------------------------------------------
        # MIDDLE: Hero Time & Art (CENTERED)
        # ------------------------------------------------
        middle_container = QWidget()
        middle_container.setStyleSheet("background-color: transparent;") # Crucial
        middle_layout = QHBoxLayout(middle_container)
        middle_layout.setSpacing(60) # Gap between Time and Art
        middle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center everything horizontally
        
        # Left: The Clock Group
        time_container = QWidget()
        time_container.setStyleSheet("background-color: transparent;")
        time_layout = QVBoxLayout(time_container)
        time_layout.setSpacing(0)
        time_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.time_label = QLabel("11:11")
        self.time_label.setStyleSheet("color: #FFFFFF; background-color: transparent;")
        self.add_shadow(self.time_label) # Helper to add contrast shadow
        
        self.date_label = QLabel("FEB 08")
        self.date_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background-color: transparent;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.add_shadow(self.date_label)
        
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.date_label)
        
        # Right: The Album Art Card
        self.album_card = QLabel()
        self.album_card.setFixedSize(250, 250)
        # The background color here is just a fallback placeholder
        self.album_card.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 20px;")
        self.album_card.setScaledContents(True)
        self.album_card.hide() 
        
        # Add shadow to the album card itself
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(50)
        card_shadow.setColor(QColor(0, 0, 0, 120))
        card_shadow.setOffset(0, 20)
        self.album_card.setGraphicsEffect(card_shadow)

        middle_layout.addWidget(time_container)
        middle_layout.addWidget(self.album_card)
        
        self.main_layout.addWidget(middle_container, 2)
        
        self.main_layout.addStretch(1)
        
        # ------------------------------------------------
        # BOTTOM: Artist Info
        # ------------------------------------------------
        self.song_info_container = QWidget()
        self.song_info_container.setStyleSheet("background-color: transparent;")
        info_layout = QVBoxLayout(self.song_info_container)
        info_layout.setSpacing(5)
        
        self.song_title = QLabel("Song Title")
        self.song_title.setStyleSheet("color: #FFFFFF; background-color: transparent;")
        self.song_title.setWordWrap(True)
        self.add_shadow(self.song_title)
        
        self.song_artist = QLabel("Artist Name")
        self.song_artist.setStyleSheet("color: rgba(255, 255, 255, 0.7); background-color: transparent;")
        self.add_shadow(self.song_artist)
        
        info_layout.addWidget(self.song_title)
        info_layout.addWidget(self.song_artist)
        
        self.main_layout.addWidget(self.song_info_container)
        
        # ------------------------------------------------
        # LOGIC
        # ------------------------------------------------
        self.worker.gesture_signal.connect(self.update_gesture)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)
        self.update_ui()

    def add_shadow(self, widget):
        """Adds a subtle black glow behind text for readability."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180)) # Dark shadow
        shadow.setOffset(0, 0)
        widget.setGraphicsEffect(shadow)

    # --- 1. THE ATMOSPHERE: Paint the Background ---
    def paintEvent(self, event):
        painter = QPainter(self)
        
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            # Draw the blurred album art over the whole screen
            painter.drawPixmap(self.rect(), self.bg_pixmap)
            
            # Draw a dark overlay so text is readable (The "Dimmer Switch")
            # Increase alpha (last number) if text is still hard to read
            painter.fillRect(self.rect(), QColor(0, 0, 0, 160)) 
        else:
            # Fallback Dark Grey
            painter.fillRect(self.rect(), QColor("#121212"))

    # --- 2. RESPONSIVE FONTS ---
    def resizeEvent(self, event):
        h = self.height()
        
        # Hero Time (Huge)
        self.time_label.setFont(QFont("Urbanist", int(h * 0.15), QFont.Weight.Bold))
        
        # Date (Small, spaced)
        date_font = QFont("Urbanist", int(h * 0.03), QFont.Weight.Medium)
        date_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        self.date_label.setFont(date_font)
        
        # Title & Artist
        self.song_title.setFont(QFont("Urbanist", int(h * 0.06), QFont.Weight.Bold))
        self.song_artist.setFont(QFont("Urbanist", int(h * 0.03)))
        
        super().resizeEvent(event)

    def update_gesture(self, gesture):
        self.gesture_label.setText(gesture.upper())

    def update_ui(self):
        now = datetime.datetime.now()
        self.time_label.setText(now.strftime("%I:%M"))
        self.date_label.setText(now.strftime("%b %d").upper())
        self.update_song_info()

    # --- ROUNDED IMAGE HELPER ---
    def get_rounded_pixmap(self, pixmap, radius=20):
        """Crops a QPixmap to have rounded corners."""
        if pixmap.isNull(): return pixmap
        
        # Create a transparent target image
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)
        
        # Paint onto it
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create the rounded path
        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
        
        # Clip to the path and draw the original image
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    # --- ALBUM ART LOGIC ---
    def update_song_info(self):
        song_info = self.get_spotify_info() or self.get_music_info()
        
        if song_info:
            self.song_title.setText(song_info['song'])
            self.song_artist.setText(song_info['artist'])
            
            song_id = f"{song_info['song']}|{song_info['artist']}"
            if song_id != self.current_song_id:
                self.current_song_id = song_id
                
                pixmap = None
                if song_info['source'] == 'music':
                    pixmap = self.get_album_art_from_music()
                
                if pixmap and not pixmap.isNull():
                    # 1. Update the small card (With Rounded Corners!)
                    rounded_pixmap = self.get_rounded_pixmap(pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                    self.album_card.setPixmap(rounded_pixmap)
                    self.album_card.show()
                    
                    # 2. Update the Background (Cheap Blur)
                    small_img = pixmap.scaled(50, 50, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.bg_pixmap = small_img.scaled(self.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    self.update() 
                else:
                    self.album_card.hide()
                    self.bg_pixmap = None
                    self.update()
        else:
            self.current_song_id = None
            self.song_title.setText("NOT PLAYING")
            self.song_artist.setText("")
            self.album_card.hide()
            self.bg_pixmap = None
            self.update()

    # (Keep your existing helpers exactly as they were)
    def get_spotify_info(self):
        script = '''if application "Spotify" is running then
            tell application "Spotify"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|spotify"
                end if
            end tell
        end if
        return ""'''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=1)
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    return {'song': parts[0], 'artist': parts[1], 'source': 'spotify'}
        except: pass
        return None
    
    def get_music_info(self):
        script = '''if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|music"
                end if
            end tell
        end if
        return ""'''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=1)
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    return {'song': parts[0], 'artist': parts[1], 'source': 'music'}
        except: pass
        return None

    def get_album_art_from_music(self):
        temp_file = os.path.join(tempfile.gettempdir(), "gesturly_album_art.jpg")
        script = f'''
        if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    try
                        set artworkData to data of artwork 1 of current track
                        set fileRef to open for access POSIX file "{temp_file}" with write permission
                        set eof fileRef to 0
                        write artworkData to fileRef
                        close access fileRef
                        return "success"
                    on error
                        return "error"
                    end try
                end if
            end tell
        end if
        return "not_playing"
        '''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=2)
            if "success" in result.stdout:
                return QPixmap(temp_file)
        except: pass
        return None

# --- Video Feed Page ---
     
class VideoFeedPage(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        layout = QVBoxLayout(self)
        title = QLabel("VIDEO FEED")
        title.setFont(QFont("Six Caps", 60))
        title.setStyleSheet("color: #F7FFE3;")
        layout.addWidget(title)
        
        # Camera Feed
        self.feed_label = AspectLabel()
        self.feed_label.setText("Loading Camera...")
        self.feed_label.setStyleSheet("background-color: #000; border-radius: 10px;")
        self.feed_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.feed_label)
        
        self.gesture_status = QLabel("State: No Hand")
        self.gesture_status.setFont(QFont("Urbanist", 18))
        self.gesture_status.setStyleSheet("color: #F7FFE3; margin-top: 10px;")
        self.gesture_status.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.gesture_status)
        
        # Signals
        self.worker.change_pixmap_signal.connect(self.update_video_feed)
        self.worker.gesture_signal.connect(self.update_gesture_label)
        
    def update_video_feed(self, qt_image):
       self.feed_label.setPixmap(QPixmap.fromImage(qt_image))

    def update_gesture_label(self, gesture_text):
        self.gesture_status.setText(f"State: {gesture_text}")

# --- Contribute Page ---

class ContributePage(QWidget):
    def __init__(self):
        super().__init__()
        
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Title
        title = QLabel("Made with <3")
        title.setFont(QFont("Urbanist", 40, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF; background-color: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 2. The Story (Exhibition Text)
        story_text = """
        <p style='line-height: 140%;'>
        This project was brought to life in just a few days as a 
        <b>Student Exhibition</b> piece. It is a testament to what can be achieved 
        when curiosity meets deadlines.
        </p>
        <p style='line-height: 140%;'>
        We stand on the shoulders of giants. This software exists thanks to the 
        incredible <b>Open Source</b> community and the tools they share with the world.
        If you find value in this project, consider contributing back. Whether it's code, design, documentation, or just spreading the word - every bit helps. 
        You can reuse the code, build upon it, or even just share your thoughts. Let's keep the spirit of collaboration alive!
        </p>
        """
        story = QLabel(story_text)
        story.setFont(QFont("Urbanist", 18))
        story.setStyleSheet("color: rgba(255, 255, 255, 0.7); background-color: transparent;")
        story.setAlignment(Qt.AlignmentFlag.AlignCenter)
        story.setWordWrap(True)
        # Limit width so lines aren't too long to read
        story.setFixedWidth(500) 
        layout.addWidget(story)

        # 3. The Call to Action (Link)
        # We use HTML styling inside the text to color the link
        link_text = """
        <a href='https://github.com/xdd-cz/Gesturly' style='color: #F7FFE3; text-decoration: none; font-weight: bold;'>
            CONTRIBUTE ON GITHUB &rarr;
        </a>
        """
        link_label = QLabel(link_text)
        link_label.setFont(QFont("Urbanist", 16))
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- THE MAGIC FOR LINKS ---
        link_label.setOpenExternalLinks(True) 
        link_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # ---------------------------
        
        layout.addWidget(link_label)

        # Spacer to push everything to visual center
        layout.addStretch()

# 5. Main Window

class GesturlyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesturly")
        self.resize(1000, 600)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #28332E; color: #F7FFE3")
        
        QFontDatabase.addApplicationFont("fonts/SixCaps-Regular.ttf")
        QFontDatabase.addApplicationFont("fonts/Urbanist-VariableFont_wght.ttf")
        
        self.thread = GestureWorker()
        self.thread.start()
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(250)
        sidebar.setStyleSheet("background-color: #9a9a9a;")
        
        side_layout = QVBoxLayout(sidebar)
        side_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        side_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Gesturly")
        title.setFont(QFont("Urbanist", 20, QFont.Weight.Medium))
        side_layout.addWidget(title)
        
        panel = QLabel("Panel")
        panel.setFont(QFont("Urbanist", 10))
        side_layout.addWidget(panel)
        
        self.stack = QStackedWidget()
        self.home_page = HomePage(self.thread)
        self.settings_page = SettingsPage()
        self.big_picture_page = BigPicturePage(self.thread)
        self.video_feed_page = VideoFeedPage(self.thread)
        self.contribute_page = ContributePage()
        
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.big_picture_page)
        self.stack.addWidget(self.video_feed_page)
        self.stack.addWidget(self.contribute_page)
        
        self.create_nav_link("Home", 0, side_layout)
        self.create_nav_link("Settings", 1, side_layout)
        self.create_nav_link("Big picture", 2, side_layout)
        self.create_nav_link("Video feed", 3, side_layout)
        self.create_nav_link("Contribute", 4, side_layout)
        
        main_layout.addWidget(sidebar, 0) # Sidebar fits content
        main_layout.addWidget(self.stack, 1) # Stack takes rest

    def create_nav_link(self, text, index, layout):
        label = ClickableLabel(text)
        label.setFont(QFont("Urbanist", 14))
        label.clicked.connect(lambda: self.stack.setCurrentIndex(index))
        layout.addWidget(label)

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GesturlyUI()
    window.show()
    sys.exit(app.exec())