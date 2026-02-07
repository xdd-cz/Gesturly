import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt

class GlowingLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        # 1. Font Setup (Tall and narrow like the image)
        # If you don't have "Six Caps", "Impact" or "Arial Narrow" is a close fallback
        self.setFont(QFont("Six Caps", 120)) 
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 2. Text Color (Very pale, almost white-green)
        self.setStyleSheet("color: #F2FFE3;") 

        # 3. The Glow Effect
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(50)         # High radius = soft spread
        self.glow.setColor(QColor("#D4FF88")) # The "Lime/Chartreuse" glow color
        self.glow.setOffset(0, 0)           # Center the glow
        
        self.setGraphicsEffect(self.glow)

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(500, 300)
        
        # Dark Green/Black background from your image
        self.setStyleSheet("background-color: #1b2621;") 
        
        layout = QVBoxLayout(self)
        
        # Load font if you have it, otherwise it uses system default
        QFontDatabase.addApplicationFont("fonts/SixCaps-Regular.ttf")
        
        label = GlowingLabel("11:11")
        layout.addWidget(label)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())