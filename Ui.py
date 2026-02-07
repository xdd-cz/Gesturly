import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QFrame
)
from PyQt6.QtGui import QFontDatabase, QFont, QColor
from PyQt6.QtCore import Qt


class GesturlyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesturly")
        self.setFixedSize(798, 482)
        self.setStyleSheet("background-color: #2b3530;")

        # Load fonts
        QFontDatabase.addApplicationFont("fonts/Nabla-Regular.ttf")
        QFontDatabase.addApplicationFont("fonts/Urbanist-Regular.ttf")

        nabla = "Nabla"
        urbanist = "Urbanist"

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ---------------- Sidebar ----------------
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sidebar.setStyleSheet("""
            background-color: rgba(40, 40, 40, 0);
            border-radius: 16px;
        """)

        side_layout = QVBoxLayout(sidebar)
        side_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        side_layout.setContentsMargins(21, 21, 21, 21)

        title = QLabel("Gesturly")
        title.setFont(QFont(urbanist, 20, QFont.Weight.Bold))
        side_layout.addWidget(title)

        for item in ["Home", "Settings", "Big picture", "Video feed", "Contribute", "About"]:
            label = QLabel(item)
            label.setFont(QFont(urbanist, 14))
            side_layout.addWidget(label)

        # ---------------- Center ----------------
        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(21, 30, 21, 30)
        center.setStyleSheet("background-color: #2b3530;")

        home_title = QLabel("Home")
        home_title.setFont(QFont(nabla, 40))
        center_layout.addWidget(home_title)

        body = QLabel(
            "Welcome to gesturly. Start controlling your music with\n"
            "gesture and style.\n"
            "Learn how to use gesturly with our easy tutorial, or\n"
            "customise gesturly to your liking in the setting panel.\n"
            "Have fun being cool :)"
        )
        body.setFont(QFont(urbanist, 10))
        body.setStyleSheet("color: #e5e5e5;")
        center_layout.addWidget(body)

        how_to = QLabel("How to:")
        how_to.setFont(QFont(nabla, 20))
        center_layout.addWidget(how_to)

        how_box = QFrame()
        how_box.setFixedHeight(200)
        how_box.setStyleSheet("background-color: #e6e6e6;")
        center_layout.addWidget(how_box)

        # ---------------- Now Playing ----------------
        now_playing = QFrame()
        now_layout = QVBoxLayout(now_playing)
        now_layout.setContentsMargins(30, 30, 30, 30)

        now_title = QLabel("Now playing")
        now_title.setFont(QFont(nabla, 40))
        now_layout.addWidget(now_title)

        album_art = QFrame()
        album_art.setFixedSize(300, 300)
        album_art.setStyleSheet("background-color: #e6e6e6;")
        now_layout.addWidget(album_art)

        song_title = QLabel("Title")
        song_title.setFont(QFont(nabla, 40))
        now_layout.addWidget(song_title)

        artist = QLabel("Artist")
        artist.setFont(QFont(nabla, 20))
        artist.setStyleSheet("color: #e5e5e5;")
        now_layout.addWidget(artist)

        # ---------------- Assemble ----------------
        main_layout.addWidget(sidebar)
        main_layout.addWidget(center, 1)
        main_layout.addWidget(now_playing, 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GesturlyUI()
    window.show()
    sys.exit(app.exec())
