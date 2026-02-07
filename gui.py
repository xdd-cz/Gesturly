import sys
import subprocess
import os
import tempfile
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QFrame
)
from PyQt6.QtGui import QFontDatabase, QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer

class GesturlyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesturly")
        self.setFixedSize(798, 482)
        self.setStyleSheet("background-color: #28332E; color: #F7FFE3")
        
        # Track current song to avoid re-downloading same album art
        self.current_song_id = None
        
        # Load fonts
        QFontDatabase.addApplicationFont("fonts/SixCaps-Regular.ttf")
        QFontDatabase.addApplicationFont("fonts/Urbanist-VariableFont_wght.ttf")
        nabla = "Six Caps"
        urbanist = "Urbanist"
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #9a9a9a;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        side_layout.setContentsMargins(21, 21, 21, 21)
        
        title = QLabel("Gesturly")
        title.setFont(QFont(urbanist, 20, QFont.Weight.Medium))
        side_layout.addWidget(title)
        
        panel = QLabel("Panel")
        panel.setFont(QFont(urbanist, 10))
        side_layout.addWidget(panel)
        
        for item in ["Home", "Settings", "Big picture", "Video feed", "Contribute", "About"]:
            label = QLabel(item)
            label.setFont(QFont(urbanist, 14))
            side_layout.addWidget(label)
        
        # Introduction
        intro = QFrame()
        intro.setFixedWidth(299)
        intro_layout = QVBoxLayout(intro)
        intro_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        intro_layout.setContentsMargins(21, 10, 21, 21)
        intro.setStyleSheet("background-color: #28332E;")
        
        home_title = QLabel("HOME")
        home_title.setFont(QFont(nabla, 60))
        home_title.setStyleSheet("color: #F7FFE3 !important;")
        intro_layout.addWidget(home_title)
        
        body = QLabel(
            "Welcome to gesturly. Start controlling your music<br> with simple hand gestures. Use the sidebar to <br>navigate through different sections of the app. <br> Have fun being cool :D"
        )
        body.setFont(QFont(urbanist, 12))
        intro_layout.addWidget(body)
        
        cam = QLabel("Camera feed")
        cam.setFont(QFont(nabla, 30))
        intro_layout.addWidget(cam)
        
        # cam feed here
        
        
        # Now Playing
        playing = QFrame()
        playing_layout = QVBoxLayout(playing)
        playing_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        playing_layout.setContentsMargins(21, 10, 21, 21)
        playing.setStyleSheet("background-color: #252F2A;")
        
        title_label = QLabel("Now Playing")
        title_label.setFont(QFont(nabla, 60))
        title_label.setStyleSheet("color: #F7FFE3 !important;")
        playing_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # Album art
        self.album_art_label = QLabel("🎵")
        self.album_art_label.setFixedSize(250, 250)
        self.album_art_label.setStyleSheet("""
            background-color: #1a1a1a;
        """)
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_label.setFont(QFont(nabla, 100))
        self.album_art_label.setScaledContents(True)
        playing_layout.addWidget(self.album_art_label)
        
        # Song title
        self.song_title = QLabel("Not Playing")
        self.song_title.setFont(QFont(urbanist, 20, QFont.Weight.DemiBold))
        self.song_title.setStyleSheet("color: #F7FFE3 !important;")
        self.song_title.setWordWrap(True)
        playing_layout.addWidget(self.song_title)
        
        # Artist
        self.song_artist = QLabel("Play a song to start")
        self.song_artist.setFont(QFont(urbanist, 14))
        self.song_artist.setStyleSheet("color: #cccccc !important;")
        self.song_artist.setWordWrap(True)
        playing_layout.addWidget(self.song_artist)
        
        # Output area
        main_layout.addWidget(sidebar)
        main_layout.addWidget(intro)
        main_layout.addWidget(playing)
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_song_info)
        self.update_timer.start(2000)  # Every 2 seconds
        
        # Initial update
        self.update_song_info()
    
    def get_spotify_info(self):
        """Get song from Spotify desktop app"""
        script = '''
        if application "Spotify" is running then
            tell application "Spotify"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|spotify"
                end if
            end tell
        end if
        return ""
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=1)
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    return {
                        'song': parts[0], 
                        'artist': parts[1],
                        'source': 'spotify'
                    }
        except Exception as e:
            print(f"Spotify error: {e}")
        return None
    
    def get_music_info(self):
        """Get song from Apple Music app"""
        script = '''
        if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    return name of current track & "|" & artist of current track & "|music"
                end if
            end tell
        end if
        return ""
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=1)
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    return {
                        'song': parts[0], 
                        'artist': parts[1],
                        'source': 'music'
                    }
        except Exception as e:
            print(f"Music error: {e}")
        return None
    
    def get_album_art_from_music(self):
        """Extract album art from Apple Music app"""
        temp_file = os.path.join(tempfile.gettempdir(), "gesturly_album_art.jpg")
        
        # Remove old temp file if exists
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        
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
                    on error errMsg
                        return "error: " & errMsg
                    end try
                end if
            end tell
        end if
        return "not_playing"
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=5)
            
            output = result.stdout.strip()
            print(f"Album art extraction result: {output}")
            
            if output == "success" and os.path.exists(temp_file):
                # Try to load the image
                pixmap = QPixmap(temp_file)
                if not pixmap.isNull():
                    print("✅ Album art loaded successfully!")
                    return pixmap
                else:
                    print("❌ Failed to load image from file")
            else:
                print(f"❌ Extraction failed: {output}")
                
        except Exception as e:
            print(f"❌ Album art error: {e}")
        
        return None
    
    def get_album_art_from_spotify(self):
        """Spotify doesn't support album art extraction via AppleScript easily"""
        # For Spotify, we'd need the API (which is down)
        # So we'll just return None for now
        return None
    
    def update_song_info(self):
        """Update display with current song"""
        # Try Spotify first, then Apple Music
        song_info = self.get_spotify_info() or self.get_music_info()
        
        if song_info:
            song_id = f"{song_info['song']}|{song_info['artist']}"
            
            # Update text
            self.song_title.setText(song_info['song'])
            self.song_artist.setText(song_info['artist'])
            
            # Only update album art if song changed (to avoid constant re-downloading)
            if song_id != self.current_song_id:
                self.current_song_id = song_id
                
                # Try to get album art
                pixmap = None
                if song_info['source'] == 'music':
                    pixmap = self.get_album_art_from_music()
                elif song_info['source'] == 'spotify':
                    pixmap = self.get_album_art_from_spotify()
                
                if pixmap:
                    # Scale and display album art
                    scaled = pixmap.scaled(
                        200, 200, 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.album_art_label.setPixmap(scaled)
                    self.album_art_label.setText("")
                    self.album_art_label.setStyleSheet("""
                        background-color: #1a1a1a; 
                    """)
                else:
                    # No album art available, show playing symbol
                    self.album_art_label.clear()
                    self.album_art_label.setText("▶️")
                    self.album_art_label.setFont(QFont("Six Caps", 100))
                    self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.album_art_label.setStyleSheet("""
                        background-color: #1a1a1a; 
                        border: 3px solid #F7FFE3;
                        border-radius: 10px;
                    """)
        else:
            # No song playing
            self.current_song_id = None
            self.song_title.setText("Not Playing")
            self.song_artist.setText("Play Spotify or Apple Music")
            
            self.album_art_label.clear()
            self.album_art_label.setText("🎵")
            self.album_art_label.setFont(QFont("Six Caps", 100))
            self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.album_art_label.setStyleSheet("""
                background-color: #1a1a1a; 
                border: 3px solid #F7FFE3;
                border-radius: 10px;
            """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GesturlyUI()
    window.show()
    sys.exit(app.exec())