import sys
import subprocess
import os
import tempfile
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QFrame, QStackedWidget, QGridLayout, 
    QSlider, QComboBox, QCheckBox, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QPixmap, QCursor, QColor, QPainter, QPainterPath
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from gesture_worker import GestureWorker

# Music Logic
class MusicHandler:
    """Handles all AppleScript logic in one place to avoid code duplication."""
    
    @staticmethod
    def get_info():
        # Check Spotify
        script_spot = '''if application "Spotify" is running then
            tell application "Spotify"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|spotify"
                end if
            end tell
        end if
        return ""'''
        
        # Check Apple Music
        script_music = '''if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|music"
                end if
            end tell
        end if
        return ""'''
        
        for script in [script_spot, script_music]:
            try:
                result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=0.5)
                if result.stdout.strip():
                    parts = result.stdout.strip().split('|')
                    if len(parts) >= 2:
                        return {'song': parts[0], 'artist': parts[1], 'source': parts[2] if len(parts) > 2 else 'music'}
            except: 
                continue
        return None

    @staticmethod
    def get_album_art():
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
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=1)
            if "success" in result.stdout:
                return QPixmap(temp_file)
        except: pass
        return None


# CUSTOM UI COMPONENTS
class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class AspectLabel(QLabel):
    """A Label that scales images smoothly without losing aspect ratio."""
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

# PAGES
class HomePage(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.setStyleSheet("background-color: #101010;") 
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- CAM ---
        intro = QFrame()
        intro.setStyleSheet("background-color: #1A1A1A; border-right: 1px solid #333;")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(40, 40, 40, 40)
        
        home_title = QLabel("HOME")
        home_title.setFont(QFont("Six Caps", 60))
        home_title.setStyleSheet("color: #F7FFE3;")
        intro_layout.addWidget(home_title)
        
        body = QLabel("Welcome to Gesturly. Control your music with simple hand gestures.")
        body.setFont(QFont("Urbanist", 16))
        body.setStyleSheet("color: #CCC;")
        body.setWordWrap(True)
        intro_layout.addWidget(body)
        
        self.feed_label = AspectLabel()
        self.feed_label.setStyleSheet("background-color: #000; border-radius: 12px; border: 1px solid #333;")
        self.feed_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        intro_layout.addWidget(self.feed_label)
        
        self.gesture_status = QLabel("State: NO HAND")
        self.gesture_status.setFont(QFont("Urbanist", 18, QFont.Weight.Bold))
        self.gesture_status.setStyleSheet("color: #F7FFE3; margin-top: 10px;")
        self.gesture_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(self.gesture_status)
        
        # --- Now playing ---
        playing = QFrame()
        playing.setStyleSheet("background-color: #101010;")
        playing.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        playing_layout = QVBoxLayout(playing)
        playing_layout.setContentsMargins(40, 40, 40, 40)
        
        title_label = QLabel("NOW PLAYING")
        title_label.setFont(QFont("Six Caps", 60))
        title_label.setStyleSheet("color: #F7FFE3;")
        playing_layout.addWidget(title_label)
        
        self.album_art_label = AspectLabel()
        self.album_art_label.setText("🎵")
        self.album_art_label.setStyleSheet("background-color: #222; border-radius: 20px;")
        self.album_art_label.setMinimumSize(250, 250)
        playing_layout.addWidget(self.album_art_label)
        
        self.song_title = QLabel("Not Playing")
        self.song_title.setFont(QFont("Urbanist", 24, QFont.Weight.Bold))
        self.song_title.setStyleSheet("color: #FFFFFF;")
        self.song_title.setWordWrap(True)
        playing_layout.addWidget(self.song_title)
        
        self.song_artist = QLabel("Open Spotify or Music")
        self.song_artist.setFont(QFont("Urbanist", 16))
        self.song_artist.setStyleSheet("color: #888;")
        playing_layout.addWidget(self.song_artist)
        
        layout.addWidget(intro, 6) # 60% Width
        layout.addWidget(playing, 4) # 40% Width

        # Logic
        self.worker.change_pixmap_signal.connect(lambda img: self.feed_label.setPixmap(QPixmap.fromImage(img)))
        self.worker.gesture_signal.connect(lambda txt: self.gesture_status.setText(f"State: {txt}"))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_song)
        self.timer.start(2000)
        self.update_song()

    def update_song(self):
        info = MusicHandler.get_info()
        if info:
            self.song_title.setText(info['song'])
            self.song_artist.setText(info['artist'])
            
            # Get Art
            pix = None
            if info['source'] == 'music':
                pix = MusicHandler.get_album_art()
            
            if pix and not pix.isNull():
                self.album_art_label.setPixmap(pix)
            else:
                self.album_art_label.setText("🎵")
        else:
            self.song_title.setText("Not Playing")
            self.album_art_label.clear()

class BigPicturePage(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.current_song_id = None
        self.bg_pixmap = None
        
        self.setStyleSheet("background-color: #101010; color: #F7FFE3;")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(60, 60, 60, 60)
        
        # gesture status
        self.gesture_label = QLabel("NO HAND")
        font = QFont("Urbanist", 14, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        self.gesture_label.setFont(font)
        self.gesture_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background-color: transparent;")
        self.main_layout.addWidget(self.gesture_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.main_layout.addStretch(1)
        
        # time and art
        middle_container = QWidget()
        middle_container.setStyleSheet("background-color: transparent;")
        middle_layout = QHBoxLayout(middle_container)
        middle_layout.setSpacing(60)
        middle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # clock
        time_container = QWidget()
        time_container.setStyleSheet("background-color: transparent;")
        time_layout = QVBoxLayout(time_container)
        time_layout.setSpacing(0)
        time_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.time_label = QLabel("11:11")
        self.time_label.setStyleSheet("color: #F7FFE3; background-color: transparent;")
        self.add_shadow(self.time_label)
        
        self.date_label = QLabel("JAN 01")
        self.date_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background-color: transparent;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.add_shadow(self.date_label)
        
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.date_label)
        
        # album
        self.album_card = QLabel()
        self.album_card.setFixedSize(250, 250)
        self.album_card.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 20px;")
        self.album_card.setScaledContents(True)
        self.album_card.hide()
        
        # shadwo
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(50)
        card_shadow.setColor(QColor(0, 0, 0, 120))
        card_shadow.setOffset(0, 20)
        self.album_card.setGraphicsEffect(card_shadow)

        middle_layout.addWidget(time_container)
        middle_layout.addWidget(self.album_card)
        self.main_layout.addWidget(middle_container, 2)
        self.main_layout.addStretch(1)
        
        # song info
        self.song_info_container = QWidget()
        self.song_info_container.setStyleSheet("background-color: transparent;")
        info_layout = QVBoxLayout(self.song_info_container)
        
        self.song_title = QLabel("Song Title")
        self.song_title.setStyleSheet("color: #F7FFE3; background-color: transparent;")
        self.add_shadow(self.song_title)
        
        self.song_artist = QLabel("Artist")
        self.song_artist.setStyleSheet("color: rgba(255, 255, 255, 0.7); background-color: transparent;")
        self.add_shadow(self.song_artist)
        
        info_layout.addWidget(self.song_title)
        info_layout.addWidget(self.song_artist)
        self.main_layout.addWidget(self.song_info_container)
        
        self.worker.gesture_signal.connect(lambda g: self.gesture_label.setText(g.upper()))
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)
        self.update_ui()

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        widget.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            painter.drawPixmap(self.rect(), self.bg_pixmap)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 160)) # Overlay
        else:
            painter.fillRect(self.rect(), QColor("#101010"))

    def resizeEvent(self, event):
        h = self.height()
        self.time_label.setFont(QFont("Urbanist", max(40, int(h * 0.15)), QFont.Weight.Bold))
        
        d_font = QFont("Urbanist", max(14, int(h * 0.03)), QFont.Weight.Medium)
        d_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        self.date_label.setFont(d_font)
        
        self.song_title.setFont(QFont("Urbanist", max(24, int(h * 0.06)), QFont.Weight.Bold))
        self.song_artist.setFont(QFont("Urbanist", max(18, int(h * 0.03))))
        super().resizeEvent(event)

    def update_ui(self):
        now = datetime.datetime.now()
        self.time_label.setText(now.strftime("%I:%M"))
        self.date_label.setText(now.strftime("%b %d").upper())
        self.update_music()

    def get_rounded_pixmap(self, pixmap, radius=20):
        if pixmap.isNull(): return pixmap
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    def update_music(self):
        info = MusicHandler.get_info()
        if info:
            self.song_title.setText(info['song'])
            self.song_artist.setText(info['artist'])
            
            s_id = f"{info['song']}{info['artist']}"
            if s_id != self.current_song_id:
                self.current_song_id = s_id
                pix = None
                if info['source'] == 'music':
                    pix = MusicHandler.get_album_art()
                
                if pix and not pix.isNull():
                    scaled_card = pix.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    self.album_card.setPixmap(self.get_rounded_pixmap(scaled_card))
                    self.album_card.show()
                    
                    small = pix.scaled(50, 50, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.bg_pixmap = small.scaled(self.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
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

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #101010;") # FIX
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 60, 60, 60)
        main_layout.setSpacing(40)
        
        # Tutorial
        title_tut = QLabel("GESTURE GUIDE")
        title_tut.setFont(QFont("Urbanist", 24, QFont.Weight.Bold))
        title_tut.setStyleSheet("color: #FFFFFF;")
        main_layout.addWidget(title_tut)

        grid = QGridLayout()
        grid.setSpacing(20)
        grid.addWidget(self.create_card("✋", "OPEN PALM", "Does nothing"), 0, 0)
        grid.addWidget(self.create_card("👍", "THUMBS UP", "Volume Up"), 0, 1)
        grid.addWidget(self.create_card("👎", "THUMBS DOWN", "Volume Down"), 1, 0)
        grid.addWidget(self.create_card("👌", "OKAY", "Play / Pause"), 1, 1)
        main_layout.addLayout(grid)

        # Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #333;")
        main_layout.addWidget(line)

        # Prefs
        title_set = QLabel("PREFERENCES")
        title_set.setFont(QFont("Urbanist", 24, QFont.Weight.Bold))
        title_set.setStyleSheet("color: #FFFFFF;")
        main_layout.addWidget(title_set)

        # Fake Controls for visuals
        combo = QComboBox()
        combo.addItems(["FaceTime HD Camera", "External Webcam"])
        combo.setStyleSheet("background: #222; color: white; padding: 10px; border-radius: 8px;")
        main_layout.addWidget(combo)

        check = QCheckBox("Show Hand Skeleton (Debug)")
        check.setStyleSheet("color: white; font-size: 16px;")
        main_layout.addWidget(check)
        
        main_layout.addStretch()

    def create_card(self, icon, title, desc):
        card = QFrame()
        card.setStyleSheet("background-color: #1A1A1A; border-radius: 15px; border: 1px solid #333;")
        l = QVBoxLayout(card)
        l.setContentsMargins(20,20,20,20)
        
        i_lbl = QLabel(icon)
        i_lbl.setFont(QFont("Segoe UI Emoji", 30))
        i_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        i_lbl.setStyleSheet("border: none; background: transparent;")
        
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Urbanist", 14, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #F7FFE3; border: none; background: transparent;")
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color: #888; border: none; background: transparent;")
        d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        l.addWidget(i_lbl)
        l.addWidget(t_lbl)
        l.addWidget(d_lbl)
        return card

class ContributePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #101010;") # FIX
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Made with ❤")
        title.setFont(QFont("Urbanist", 40, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        story_text = """
        <p style='font-size:18px; color:#CCC;'>
        Gesturly was created for an exibition with the goal of simplifying music and making kids want to get into coding.
        It was built in a weekend using Python, PyQt6, and MediaPipe for hand tracking.
        The project is open-source and welcomes contributions from developers of all skill levels.
        This project is still in its early stages and anyone interested in helping out is encouraged to check out the repository and contributing.
        </p>
        """
        story = QLabel(story_text)
        story.setFont(QFont("Urbanist", 18))
        story.setStyleSheet("background: transparent;")
        story.setAlignment(Qt.AlignmentFlag.AlignCenter)
        story.setWordWrap(True)
        story.setFixedWidth(500) 
        layout.addWidget(story)

        # Link
        link_text = """
        <a href='https://github.com/xdd-cz/Gesturly' style='color: #F7FFE3; text-decoration: none; font-weight: bold; font-size: 20px;'>
            CONTRIBUTE ON GITHUB &rarr;
        </a>
        """
        link_label = QLabel(link_text)
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setOpenExternalLinks(True) 
        link_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        link_label.setStyleSheet("background: transparent;")
        layout.addWidget(link_label)
        layout.addStretch()

# main Window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesturly")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #101010;")

        # Start Camera Thread
        self.worker = GestureWorker()
        self.worker.start()

        # Layout: Sidebar + Stack
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet("background-color: #0A0A0A; border-right: 1px solid #222;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 20, 0, 20)
        side_layout.setSpacing(30)

        # Nav Buttons
        self.btn_home = self.create_nav_btn("⌂", 0)
        self.btn_big = self.create_nav_btn("⤢", 1)
        self.btn_set = self.create_nav_btn("⊙", 2)
        self.btn_dev = self.create_nav_btn("⌖", 3)

        side_layout.addWidget(self.btn_home)
        side_layout.addWidget(self.btn_big)
        side_layout.addWidget(self.btn_set)
        side_layout.addStretch()
        side_layout.addWidget(self.btn_dev)

        # --- Content Stack ---
        self.stack = QStackedWidget()
        self.stack.addWidget(HomePage(self.worker))      # Index 0
        self.stack.addWidget(BigPicturePage(self.worker))# Index 1
        self.stack.addWidget(SettingsPage())             # Index 2
        self.stack.addWidget(ContributePage())           # Index 3

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)

    def create_nav_btn(self, text, index):
        btn = ClickableLabel(text)
        btn.setFont(QFont("Segoe UI Emoji", 24))
        btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn.setStyleSheet("color: #666;") # Default color
        
        # When clicked, switch tab and highlight
        btn.clicked.connect(lambda: self.switch_tab(index, btn))
        return btn

    def switch_tab(self, index, active_btn):
        self.stack.setCurrentIndex(index)
        
        # Reset all colors
        for b in [self.btn_home, self.btn_big, self.btn_set, self.btn_dev]:
            b.setStyleSheet("color: #666;")
        
        # Highlight active
        active_btn.setStyleSheet("color: #F7FFE3;")

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Optional: Load font globally if you have the .ttf file
    # QFontDatabase.addApplicationFont("Urbanist-Bold.ttf")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())