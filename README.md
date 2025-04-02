<img width="1407" alt="ProxyMate" src="https://github.com/user-attachments/assets/f2667043-03ac-4183-bcf5-e33f537e7078" />

📺 ProxyMate — Batch Fix Audio Channels in Video Proxies
A minimal, native macOS app that batch-converts .mp4 and .mov files to have the correct number of audio channels — perfect for fixing proxy relinking issues in Adobe Premiere Pro.

🔧 Why This Exists

Premiere Pro throws errors when trying to relink proxy files that were created with the wrong number of audio channels. This tool solves that problem by letting you:

🎯 Choose a target number of audio channels (e.g. 2, 6, 8)

📂 Select a folder of proxy videos

⚡ Batch convert them using FFmpeg (smartly adds/removes channels)

✅ Generate relinkable proxies that match original media specs

✨ Features
Drag-and-drop UI

Native macOS .app (bundled with FFmpeg)

Custom audio channel control (1–10 channels)

Live FFmpeg console output

Progress tracking and smart file skipping

Minimal, styled dark interface

🚀 Built With
Python 3

PyQt5

FFmpeg / FFprobe

PyInstaller (for macOS packaging)

### FFmpeg Licensing

This app uses [FFmpeg](https://ffmpeg.org), a free and open-source multimedia framework, under the [GPLv3 license](https://www.gnu.org/licenses/gpl-3.0.html).  
The FFmpeg binaries are included for convenience. You can obtain the source code and learn more at [https://ffmpeg.org](https://ffmpeg.org).

💻 [Download here](https://mega.nz/folder/XUYWEDwT#7CA1Md-IBPuqah05PJ0Kiw)

🧠 Created By
Colm Moore @thisiscolm www.colmmoore.com

🍺 [Buy me a beer if you found this useful](https://buymeacoffee.com/thisiscolm)

