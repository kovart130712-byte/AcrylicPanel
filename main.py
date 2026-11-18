import sys
import os
import subprocess
import ctypes
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QLineEdit, QMessageBox, QCalendarWidget, QDialog
)

APP_NAME = "AcrylicPanel"

def enable_acrylic(hwnd):
    # Windows 10 acrylic/blur effect (best effort; falls back to translucent panel).
    try:
        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [("AccentState", ctypes.c_int),
                        ("AccentFlags", ctypes.c_int),
                        ("GradientColor", ctypes.c_uint),
                        ("AnimationId", ctypes.c_int)]
        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [("Attribute", ctypes.c_int),
                        ("Data", ctypes.c_void_p),
                        ("SizeOfData", ctypes.c_size_t)]
        accent = ACCENT_POLICY(4, 2, 0xCC20242C, 0)
        data = WINDOWCOMPOSITIONATTRIBDATA(19, ctypes.addressof(accent), ctypes.sizeof(accent))
        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception:
        pass

class AcrylicPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setFixedWidth(370)
        self.setMinimumHeight(650)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget { color: #f5f7fa; font-family: Segoe UI; }
            QFrame#surface { background: rgba(29, 34, 43, 232); border: 1px solid rgba(255,255,255,35); border-radius: 22px; }
            QLabel#time { font-size: 42px; font-weight: 300; }
            QLabel#date { font-size: 14px; color: #cbd2dc; }
            QPushButton { background: rgba(255,255,255,25); border: 1px solid rgba(255,255,255,28); border-radius: 12px; padding: 13px 9px; font-size: 13px; }
            QPushButton:hover { background: rgba(255,255,255,48); }
            QPushButton:checked { background: #426da9; }
            QLineEdit { background: rgba(255,255,255,20); border: 1px solid rgba(255,255,255,35); border-radius: 12px; padding: 12px; color: white; }
            QSlider::groove:horizontal { height: 5px; background: rgba(255,255,255,55); border-radius: 2px; }
            QSlider::handle:horizontal { background: white; width: 14px; margin: -5px 0; border-radius: 7px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.surface = QFrame()
        self.surface.setObjectName("surface")
        root.addWidget(self.surface)
        layout = QVBoxLayout(self.surface)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(13)

        top = QHBoxLayout()
        self.clock = QLabel()
        self.clock.setObjectName("time")
        top.addWidget(self.clock)
        top.addStretch()
        close = QPushButton("✕")
        close.setFixedSize(38, 38)
        close.clicked.connect(self.close)
        top.addWidget(close)
        layout.addLayout(top)

        self.date_label = QLabel()
        self.date_label.setObjectName("date")
        layout.addWidget(self.date_label)
        self.update_clock()
        timer = QTimer(self)
        timer.timeout.connect(self.update_clock)
        timer.start(1000)

        layout.addWidget(self.section("Быстрые настройки"))
        grid1 = QHBoxLayout()
        self.add_toggle(grid1, "Wi-Fi", True)
        self.add_toggle(grid1, "Bluetooth")
        self.add_toggle(grid1, "Режим полёта")
        layout.addLayout(grid1)
        grid2 = QHBoxLayout()
        self.add_toggle(grid2, "Экономия")
        self.add_toggle(grid2, "Ночной свет")
        self.add_toggle(grid2, "Фокус")
        layout.addLayout(grid2)

        layout.addWidget(self.section("Звук"))
        self.add_slider(layout, "Громкость", 65)
        layout.addWidget(self.section("Яркость"))
        self.add_slider(layout, "Яркость экрана", 80)

        search = QLineEdit()
        search.setPlaceholderText("Поиск в интернете или на ПК…")
        search.returnPressed.connect(lambda: self.open_search(search.text()))
        layout.addWidget(search)

        actions = QHBoxLayout()
        for label, callback in [
            ("Переводчик", self.open_translator),
            ("Календарь", self.open_calendar),
            ("Параметры", self.open_settings),
        ]:
            b = QPushButton(label)
            b.clicked.connect(callback)
            actions.addWidget(b)
        layout.addLayout(actions)

        bottom = QHBoxLayout()
        start = QPushButton("Автозапуск: включить")
        start.clicked.connect(self.enable_startup)
        bottom.addWidget(start)
        power = QPushButton("Питание")
        power.clicked.connect(self.power_menu)
        bottom.addWidget(power)
        layout.addLayout(bottom)
        layout.addStretch(1)
        hint = QLabel("Панель для Windows 10 • нажмите Esc для закрытия")
        hint.setStyleSheet("color: rgba(255,255,255,145); font-size: 10px;")
        layout.addWidget(hint)

    def section(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-size: 15px; font-weight: 600; color: #e9edf4;")
        return label

    def add_toggle(self, row, text, checked=False):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setMinimumHeight(58)
        button.clicked.connect(lambda state, b=button: b.setText(("✓ " if state else "") + b.text().replace("✓ ", "")))
        row.addWidget(button)

    def add_slider(self, layout, name, value):
        row = QHBoxLayout()
        row.addWidget(QLabel(name))
        value_label = QLabel(str(value) + "%")
        row.addWidget(value_label)
        layout.addLayout(row)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(value)
        slider.valueChanged.connect(lambda v: value_label.setText(f"{v}%"))
        layout.addWidget(slider)

    def update_clock(self):
        now = datetime.now()
        self.clock.setText(now.strftime("%H:%M"))
        self.date_label.setText(now.strftime("%A, %d %B %Y"))

    def open_search(self, text):
        if text.strip():
            import urllib.parse, webbrowser
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(text))

    def open_translator(self):
        import webbrowser
        webbrowser.open("https://translate.google.com/")

    def open_calendar(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Календарь")
        dialog.setStyleSheet("background:#252b35;color:white;")
        box = QVBoxLayout(dialog)
        calendar = QCalendarWidget()
        box.addWidget(calendar)
        dialog.resize(330, 300)
        dialog.exec()

    def open_settings(self):
        try:
            os.startfile("ms-settings:")
        except Exception:
            pass

    def enable_startup(self):
        try:
            exe = sys.executable
            if getattr(sys, "frozen", False):
                target = exe
            else:
                target = f'"{exe}" "{os.path.abspath(__file__)}"'
            startup = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
            os.makedirs(startup, exist_ok=True)
            shortcut = os.path.join(startup, "AcrylicPanel.cmd")
            with open(shortcut, "w", encoding="utf-8") as f:
                f.write("@echo off\nstart \"\" " + target + "\n")
            QMessageBox.information(self, "Автозапуск", "Автозапуск добавлен.")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def power_menu(self):
        QMessageBox.information(self, "Питание", "Для выключения или перезагрузки используйте меню Пуск Windows.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            enable_acrylic(int(self.winId()))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, "_drag"):
            self.move(event.globalPosition().toPoint() - self._drag)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = AcrylicPanel()
    screen = app.primaryScreen().availableGeometry()
    panel.move(screen.right() - panel.width() + 1, screen.top() + 35)
    panel.show()
    sys.exit(app.exec())
