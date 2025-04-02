# main.py
import sys
import os
import subprocess
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QRadialGradient
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFrame, QDialog,
    QFileDialog, QLineEdit, QProgressBar, QTextEdit, QHBoxLayout,
    QComboBox, QSizePolicy, QMessageBox, QGraphicsOpacityEffect, QStackedLayout,
    QGraphicsDropShadowEffect, QTextBrowser
)

if sys.platform == "darwin":
    from AppKit import NSApplication, NSImage
    def set_dock_icon(icns_path):
        if os.path.exists(icns_path):
            app = NSApplication.sharedApplication()
            image = NSImage.alloc().initByReferencingFile_(icns_path)
            if image and image.isValid():
                app.setApplicationIconImage_(image)
    icon_path = os.path.join(getattr(sys, "_MEIPASS", os.getcwd()), "app.icns")
    set_dock_icon(icon_path)

def resource_path(relative_path):
    return os.path.join(getattr(sys, '_MEIPASS', os.path.abspath('.')), relative_path)


class DropOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)

        # === Frost texture load ===
        self.frost_texture = QPixmap(resource_path("assets/frost-noise.png"))
        if self.frost_texture.isNull():
            print("⚠️ Could not load frost-noise.png")

        # === Drop Card (centered content) ===
        self.card = QWidget(self)
        self.card.setFixedSize(360, 240)
        self.card.setStyleSheet("background-color: transparent; border: none;")

        layout = QVBoxLayout(self.card)
        layout.setAlignment(Qt.AlignCenter)

        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignCenter)

        # Load the image from your assets folder
        pixmap = QPixmap(resource_path("assets/dropfiles.png"))  # or .svg/.jpg
        pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # optional resizing

        self.icon.setPixmap(pixmap)

        layout.addWidget(self.icon)
        layout.addSpacing(12)

        # === Pulse animation setup ===
        self.glow_radius = 0
        self.growing = True
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_glow)
        QTimer.singleShot(100, lambda: self.pulse_timer.start(30))

    def update_glow(self):
        if self.growing:
            self.glow_radius += 0.6
            if self.glow_radius >= 15:
                self.growing = False
        else:
            self.glow_radius -= 0.6
            if self.glow_radius <= 0:
                self.growing = True

        # 🔐 Only update when the widget is shown and laid out
        if self.isVisible() and self.width() > 0 and self.height() > 0:
            self.update()

    def resizeEvent(self, event):
        self.card.move(
            (self.width() - self.card.width()) // 2,
            (self.height() - self.card.height()) // 2
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Darken background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 235))

        # Optional frost noise texture (dimmed)
        if not self.frost_texture.isNull():
            painter.setOpacity(0.08)
            for y in range(0, self.height(), self.frost_texture.height()):
                for x in range(0, self.width(), self.frost_texture.width()):
                    painter.drawPixmap(x, y, self.frost_texture)
            painter.setOpacity(1.0)

        # Neon glow
        center = self.card.geometry().center()
        center_x, center_y = center.x(), center.y()
        radius = max(self.card.width(), self.card.height()) // 2 + self.glow_radius

        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0.0, QColor(198, 54, 255, 120))
        gradient.setColorAt(1.0, QColor(0, 240, 255, 0))

        painter.setPen(QPen(QColor(198, 54, 255, 80), 3))
        painter.setBrush(gradient)
        painter.drawEllipse(
            int(center_x - radius),
            int(center_y - radius),
            int(radius * 2),
            int(radius * 2)
        )

class CustomConfirmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Output Folder Not Empty")
        self.setModal(True)
        self.setFixedSize(360, 180)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                border: 1px solid #292929;
                border-radius: 12px;
            }
            QLabel {
                color: #bbb9b7;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2b2b2b;
                color: #bbb9b7;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 8px 16px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #333;
                border: 1px solid #666;
            }
        """)

        layout = QVBoxLayout(self)
        layout.addStretch()

        label = QLabel("The output folder is not empty.\n\nDo you want to delete all files in it?")
        label.setWordWrap(True)
        layout.addWidget(label)

        layout.addStretch()
        btn_layout = QHBoxLayout()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_no = QPushButton("No")
        self.btn_yes = QPushButton("Yes")

        self.btn_cancel.clicked.connect(lambda: self.done(QDialog.Rejected))
        self.btn_no.clicked.connect(lambda: self.done(1))  # Custom return value
        self.btn_yes.clicked.connect(lambda: self.done(QDialog.Accepted))

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
        layout.addLayout(btn_layout)

class FFmpegWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(int)


    def __init__(self, input_folder, output_folder, audio_channels):
        super().__init__()
        self.processed_count = 0  # add to __init__
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.audio_channels = audio_channels
        self.ffmpeg_path = os.path.join(getattr(sys, "_MEIPASS", os.getcwd()), "ffmpeg")
        self.ffprobe_path = os.path.join(getattr(sys, "_MEIPASS", os.getcwd()), "ffprobe")
        self._is_cancelled = False  # Add this line
        self._process = None  # add to __init__

    def cancel(self):  # Add this method
        self._is_cancelled = True

    def run(self):
        try:
            files = [f for f in os.listdir(self.input_folder) if f.lower().endswith(('.mp4', '.mov'))]
            total = len(files)

            for idx, file in enumerate(files):
                if self._is_cancelled:
                    self.log.emit("⚠️ Processing cancelled by user.\n")
                    return

                input_path = os.path.join(self.input_folder, file)
                output_path = os.path.join(self.output_folder, file)
                probe_cmd = [
                    self.ffprobe_path, "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=channels", "-of", "default=noprint_wrappers=1:nokey=1", input_path
                ]
                try:
                    result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    current_channels = int(result.stdout.strip())
                except Exception as e:
                    self.log.emit(f"❌ Failed to analyze {file}: {e}")
                    continue

                if current_channels == self.audio_channels:
                    self.log.emit(f"📁 Copying {file} (already {self.audio_channels} channels)\n")
                    try:
                        import shutil
                        shutil.copy2(input_path, output_path)
                        self.processed_count += 1
                    except Exception as e:
                        self.log.emit(f"❌ Failed to copy {file}: {e}")
                    self.progress.emit(int(((idx + 1) / total) * 100))
                    continue

                cmd = [self.ffmpeg_path, "-i", input_path, "-ac", str(self.audio_channels), "-c:v", "copy", "-c:a",
                       "aac", output_path]
                self.log.emit(f"🎬 Processing {file} → {self.audio_channels}ch\n")
                self.log.emit(" ".join(cmd) + "\n")

                self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in self._process.stdout:
                    if self._is_cancelled:
                        self._process.terminate()
                        self.log.emit("⚠️ FFmpeg process terminated.\n")
                        self._process.wait()
                        return
                    self.log.emit(line.strip())
                self._process.wait()
                self.processed_count += 1  # ← count processed file
                self.progress.emit(int(((idx + 1) / total) * 100))

        finally:
            self.finished.emit(self.processed_count)


class CHNNLApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        self.setWindowTitle("ProxyMate")
        self.setFixedSize(464, 800)
        self.processing = False

        self.init_ui()
        self.drop_overlay = DropOverlay(self)
        self.drop_overlay.setGeometry(self.rect())
        self.drop_overlay.raise_()
        self.set_dark_style()

    def init_ui(self):
        self.set_dark_style()

        # === Base container ===
        base = QWidget()
        # base.setStyleSheet("background-color: #171718;")
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(base)

        # === Stacked layout for background image + UI overlay ===
        stack = QStackedLayout(base)
        stack.setStackingMode(QStackedLayout.StackAll)

        # === Background logo image ===
        self.logo_label = QLabel()
        self.logo_pixmap = QPixmap(resource_path("assets/proxymate_logo.png"))
        self.logo_label.setPixmap(self.logo_pixmap)
        self.logo_label.lower()
        self.logo_label.setScaledContents(True)
        self.logo_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.logo_label.setFixedHeight(290)  # height of the visible image portion
        self.logo_label.setStyleSheet("background-color: #000000;")
        stack.addWidget(self.logo_label)


        # === Foreground UI (transparent background) ===
        foreground = QWidget()
        stack.addWidget(foreground)
        foreground.setAttribute(Qt.WA_TranslucentBackground, True)
        # foreground.setStyleSheet("background: transparent;")
        foreground.raise_()

        layout = QVBoxLayout(foreground)
        layout.setContentsMargins(23, 30, 23, 30)
        layout.setSpacing(15)

        # === Spacer to push content slightly down into logo area ===
        layout.addSpacing(140)  # 👈 This controls how far down into the image the UI starts

        # === Input Folder ===
        layout.addWidget(QLabel("Input Folder"))
        input_row = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setReadOnly(True)
        input_btn = QPushButton("Select Folder")
        input_btn.clicked.connect(self.select_input_folder)
        input_row.addWidget(self.input_path)
        input_row.addWidget(input_btn)

        layout.addLayout(input_row)

        # === Output Folder ===
        layout.addWidget(QLabel("Output Folder"))
        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        output_btn = QPushButton("Select Folder")
        output_btn.clicked.connect(self.select_output_folder)
        output_row.addWidget(self.output_path)
        output_row.addWidget(output_btn)
        layout.addLayout(output_row)

        # === Channels ===
        layout.addWidget(QLabel("Number of Audio Channels"))
        self.channel_btns = []
        self.selected_channel = 1

        channel_btn_layout = QHBoxLayout()
        channel_btn_layout.setSpacing(7)
        channel_btn_layout.setContentsMargins(0, 0, 0, 0)
        channel_btn_layout.setAlignment(Qt.AlignLeft)

        channel_btn_container = QWidget()
        channel_btn_container.setLayout(channel_btn_layout)
        channel_btn_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for i in range(1, 9):
            btn = QPushButton(str(i))
            btn.setFixedSize(46, 36)
            btn.setProperty("selected", False)  # Initialize the property
            btn.clicked.connect(lambda checked, num=i: self.select_channel(num))
            self.channel_btns.append(btn)
            channel_btn_layout.addWidget(btn)

        layout.addWidget(channel_btn_container)
        self.select_channel(1)

        # === Start Button ===
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setFixedSize(418, 50)
        layout.addWidget(self.start_btn)



        # === Console ===
        self.console = QTextEdit()
        self.console.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #bbb9b7;
                border: 1px solid #292929;
                border-radius: 8px;
                padding: 8px;
                font-family: Menlo, Consolas, monospace;
                font-size: 13px;
            }
        """)

        self.console.setPlainText(
            "ProxyMate is ready.\n\n1. Select input folder of proxy files.\n2. Select output folder for processed proxies.\n3. Choose number of audio channels to match OCF.\n4. Click 'Start', sit back.\n\nPSA: Never process original camera files.\n\nUse at your own risk.\n"
        )
        layout.addWidget(self.console)

        # === Progress Bar ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_bar)

        footer = QTextBrowser()
        footer.setHtml("""
            <div style="text-align: center;">
                <a href="https://buymeacoffee.com/thisiscolm" style="color: #aaa;">Buy me a beer if you found this tool useful...</a>
            </div>
        """)
        footer.setOpenExternalLinks(True)
        footer.setMaximumHeight(30)
        footer.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        footer.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        footer.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
                font-size: 11px;
                color: #888888;
            }
            a:hover {
                color: #c636ff;
            }
        """)

        layout.addWidget(footer)

    def select_channel(self, number):
        self.selected_channel = number
        for btn in self.channel_btns:
            is_selected = btn.text() == str(number)
            btn.setProperty("selected", is_selected)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_path.setText(folder)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def start_processing(self):
        if self.processing:
            self.worker.cancel()
            self.console.append("⛔ Cancelling processing...\n")
            return

        input_folder = self.input_path.text()
        output_folder = self.output_path.text()
        audio_channels = self.selected_channel

        if not input_folder or not os.path.exists(input_folder):
            self.console.append("<span style='font-family: Apple Color Emoji;'>⚠️ </span> Input folder is missing or invalid.")
            return

        if not output_folder or not os.path.exists(output_folder):
            self.console.append("<span style='font-family: Apple Color Emoji;'>⚠️ </span> Output folder is missing or invalid.")
            return

        if os.path.abspath(input_folder) == os.path.abspath(output_folder):
            self.console.append(
                "<span style='font-family: Apple Color Emoji;'>🛑️ </span> Input and output folders must be different.\n")
            return

        if os.path.exists(output_folder) and os.listdir(output_folder):
            dialog = CustomConfirmDialog(self)
            reply = dialog.exec_()

            if reply == QDialog.Accepted:
                for f in os.listdir(output_folder):
                    try:
                        os.remove(os.path.join(output_folder, f))
                    except Exception as e:
                        self.console.append(f"❌ Failed to delete {f}: {e}\n")
            elif reply == QDialog.Rejected:
                self.console.append("🚫 Operation cancelled by user.\n")
                return

            if reply == QMessageBox.Yes:
                for f in os.listdir(output_folder):
                    try:
                        os.remove(os.path.join(output_folder, f))
                    except Exception as e:
                        self.console.append(f"❌ Failed to delete {f}: {e}\n")
            elif reply == QMessageBox.Cancel:
                self.console.append("🚫 Operation cancelled by user.\n")
                return

        self.worker = FFmpegWorker(input_folder, output_folder, int(audio_channels))
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.console.append)
        self.worker.finished.connect(self.on_processing_finished)


        self.processing = True

        if self.processing:
            self.start_btn.setStyleSheet("background-color: #9b2c2c; color: white;")
        else:
            self.start_btn.setStyleSheet("background-color: #e0e0e0; color: white;")
        self.start_btn.setText("Cancel Processing")
        self.worker.start()

    def on_processing_finished(self, processed_count):
        if hasattr(self, "worker") and self.worker._is_cancelled:
            self.console.append("❌  Processing was cancelled.\n")
            self.progress_bar.setValue(0)
        else:
            self.console.append(f"\n\n✅ {processed_count} file{'s' if processed_count != 1 else ''} processed.\n")
            self.progress_bar.setValue(100)

        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start")
        self.start_btn.setStyleSheet("")
        self.processing = False

        self.worker.deleteLater()
        del self.worker

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            if not self.drop_overlay.isVisible():
                self.drop_overlay.setGeometry(self.rect())
                self.drop_overlay.raise_()
                self.drop_overlay.setVisible(True)

    def dragLeaveEvent(self, event):
        self.drop_overlay.setVisible(False)

    def dropEvent(self, event):
        self.drop_overlay.setVisible(False)
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls]
        folders = [p for p in paths if os.path.isdir(p)]
        files = [p for p in paths if os.path.isfile(p)]

        if folders:
            self.input_path.setText(folders[0])
        elif files:
            self.input_path.setText(os.path.dirname(files[0]))

        self.console.append(f"📥 Dropped: {', '.join(paths)}\n")

    def selected_btn_style(self):
        return """
            QPushButton:checked {
                background-color: #c914ff;
                color: black;
                border: 1px solid #301460;
            }
        """
    def unselected_btn_style(self):
        return """
            QPushButton {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #292929;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """

    def set_dark_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: 12px;
            }

            QLabel {
                background-color: transparent;
                color: #bbb9b7;
                margin-top: 0px;
                font-weight: 500;
            }

            QLineEdit, QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 8px;
                color: #fff;
            }

            QLineEdit {
                padding: 6px;
            }

            QTextEdit {
                padding: 8px;
                border-radius: 10px;
                font-family: Menlo, Consolas, monospace;
                font-size: 13px;
            }

            QPushButton {
                background-color: #1e1e1e;
                color: #bbb9b7;
                border: 1px solid #292929;
                border-radius: 8px;
                padding: 6px 12px;
            }

            QPushButton[selected="true"] {
                background-color: #242424;
                color: #bbb9b7;
                border: 1px solid #666;
            }

            QPushButton:hover {
                background-color: #242424;
                border: 1px solid #666;
            }
            
            QLineEdit {
                background-color: #1e1e1e;
                color: #bbb9b7;
                border: 1px solid #292929;
                border-radius: 8px;
                padding: 6px;
                font-size: 14px;
            }

            QProgressBar {
                background-color: transparent;
                border: 1px solid #292929;
                border-radius: 8px;
                text-align: center;
                color: white;
            }

            QProgressBar::chunk {
                background-color: #c636ff;
                border-radius: 8px;
                margin: 0.5px;
            }
        """)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CHNNLApp()
    window.show()
    sys.exit(app.exec_())
