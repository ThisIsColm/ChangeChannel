import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource (for PyInstaller compatibility) """
    return os.path.join(getattr(sys, '_MEIPASS', os.path.abspath('.')), relative_path)
import subprocess
import ctypes
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication

if sys.platform == "darwin":
    # Set app icon in Dock (macOS only)
    from AppKit import NSApplication, NSImage
    from Foundation import NSURL


    def set_dock_icon(icns_path):
        if os.path.exists(icns_path):
            app = NSApplication.sharedApplication()
            image = NSImage.alloc().initByReferencingFile_(icns_path)
            if image and image.isValid():
                app.setApplicationIconImage_(image)
            else:
                print("⚠️ Failed to load dock icon (image invalid).")
        else:
            print("⚠️ Dock icon path not found:", icns_path)


    # Call with your .icns path
    icon_path = os.path.join(getattr(sys, "_MEIPASS", os.getcwd()), "app.icns")
    set_dock_icon(icon_path)


from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QFileDialog, QLineEdit, QProgressBar, QTextEdit, QHBoxLayout,
    QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox


class FFmpegWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, input_folder, output_folder, audio_channels):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.audio_channels = audio_channels

        # Path to bundled ffmpeg + ffprobe
        self.ffmpeg_path = os.path.join(getattr(sys, "_MEIPASS", os.getcwd()), "ffmpeg")
        self.ffprobe_path = os.path.join(getattr(sys, "_MEIPASS", os.getcwd()), "ffprobe")

    def run(self):
        files = [f for f in os.listdir(self.input_folder) if f.lower().endswith(('.mp4', '.mov'))]
        total = len(files)

        for idx, file in enumerate(files):
            input_path = os.path.join(self.input_folder, file)
            output_path = os.path.join(self.output_folder, file)

            # Step 1: Probe the file
            probe_cmd = [
                self.ffprobe_path, "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=channels",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path
            ]
            try:
                result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                current_channels = int(result.stdout.strip())
            except Exception as e:
                self.log.emit(f"❌ Failed to analyze {file}: {e}")
                continue

            target_channels = self.audio_channels
            if current_channels == target_channels:
                self.log.emit(f"🔁 Skipping {file} (already {target_channels} channels)\n")
                self.progress.emit(int(((idx + 1) / total) * 100))
                continue

            # Step 2: Run ffmpeg with -ac to change channel count
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-ac", str(target_channels),
                "-c:v", "copy",
                "-c:a", "aac",
                output_path
            ]

            self.log.emit(f"🎬 Processing {file} → {target_channels}ch\n")
            self.log.emit(" ".join(cmd) + "\n")

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            for line in process.stdout:
                self.log.emit(line.strip())

            process.wait()

            self.progress.emit(int(((idx + 1) / total) * 100))

        self.finished.emit()


class CHNNLApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Change Channel")
        self.setFixedSize(460, 700)
        self.init_ui()
        self.set_dark_style()

    def on_processing_finished(self):
        self.console.append("✅ All done.\n")
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start")

    def set_dark_style(self):

        self.setStyleSheet("""
            QWidget {
                background-color: #1d1e22;
                color: #f0f0f0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLabel {
                color: #bbbbbb;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px;
                color: #fff;
            }
            QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 8px;
                color: #dcdcdc;
                font-family: Menlo, Courier, monospace;
                font-size: 12px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QComboBox {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 2px 30px 2px 8px;  /* space for text and arrow */
                color: #fff;
                min-height: 28px;
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid #444;
            }
            
            
            QComboBox::down-arrow {{
                image: url("{caret_svg}");
                width: 15px;
                height: 15px;
            }}
 
            QProgressBar {
                height: 8px;
                background-color: #2a2a2a;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #d86001;
                border-radius: 4px;
            }
        """)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.setWindowIcon(QIcon("app.icns"))

        # Header
        icon_label = QLabel()
        icon_pixmap = QPixmap(resource_path("assets/icon.png"))

        if icon_pixmap.isNull():
            print("⚠️ Icon failed to load!")
        else:
            icon_label.setPixmap(icon_pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        title = QLabel("Change Channel")
        title.setStyleSheet("font-size: 42px; font-weight: bold; color: #e0e1e2;")


        header_layout = QHBoxLayout()
        header_layout.addWidget(icon_label)
        header_layout.addSpacing(-5)
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        version = QLabel("Regenerate video proxy files with the correct number of audio channels.")
        version.setStyleSheet("color: #888888; font-size: 11px; margin-top: -50px; margin-bottom: 12px;")
        layout.addWidget(version)

        # Input folder
        layout.addWidget(QLabel("Input Folder"))
        input_row = QHBoxLayout()
        self.input_path = QLineEdit()
        input_btn = QPushButton("Select Folder")
        input_btn.clicked.connect(self.select_input_folder)
        input_row.addWidget(self.input_path)
        input_row.addWidget(input_btn)
        layout.addLayout(input_row)

        # Output folder
        layout.addWidget(QLabel("Output Folder"))
        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        output_btn = QPushButton("Select Folder")
        output_btn.clicked.connect(self.select_output_folder)
        output_row.addWidget(self.output_path)
        output_row.addWidget(output_btn)
        layout.addLayout(output_row)

        # Audio Channels (label and dropdown on same row)
        audio_row = QHBoxLayout()
        audio_label = QLabel("Number of Audio Channels")
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
        self.channel_combo.setFixedHeight(36)
        self.channel_combo.setFixedWidth(104)
        audio_row.addWidget(audio_label)
        audio_row.addStretch()
        audio_row.addWidget(self.channel_combo)
        layout.addLayout(audio_row)

        # Start button
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_processing)
        layout.addWidget(self.start_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_bar)


        # Console log
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlainText("""
🎬 Change Channel is ready.

1. Select your input folder (MP4 or MOV files).
2. Select where you want the output files to go.
3. Choose the desired number of audio channels.
4. Click 'Start' to begin processing.

All files will be batch-processed using FFmpeg ✅

                """)

        layout.addWidget(self.console)

        bottom = QLabel("Created by Colm Moore at Tiny Ark, 2025.")
        bottom.setStyleSheet("color: #888888; font-size: 11px; margin-top: 6px; margin-bottom: 0px;")
        bottom.setAlignment(Qt.AlignCenter)

        layout.addWidget(bottom)
        self.setLayout(layout)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_path.setText(folder)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def start_processing(self):
        input_folder = self.input_path.text()
        output_folder = self.output_path.text()
        audio_channels = self.channel_combo.currentText()

        if not input_folder or not output_folder:
            self.console.append("Please select input/output folders.\n")
            return

        # 🔥 Check if output folder is empty
        if os.path.exists(output_folder) and os.listdir(output_folder):
            reply = QMessageBox.question(
                self,
                "Output Folder Not Empty",
                "The output folder is not empty.\n\nDo you want to delete all files in it?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                # Delete all files in the output folder
                for f in os.listdir(output_folder):
                    file_path = os.path.join(output_folder, f)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        self.console.append(f"❌ Failed to delete {f}: {e}")
            elif reply == QMessageBox.No:
                pass  # Just continue
            else:
                self.console.append("🚫 Operation cancelled by user.\n")
                return

        self.start_btn.setEnabled(False)
        self.start_btn.setText("Processing...")
        self.worker = FFmpegWorker(input_folder, output_folder, int(audio_channels))
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.console.append)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CHNNLApp()
    window.show()
    sys.exit(app.exec_())
