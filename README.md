![ChatGPT Image Mar 29, 2025, 05_49_27 PM](https://github.com/user-attachments/assets/9093d167-aa41-463c-b344-0ec62e4876e7)

📺 Change Channel — Batch Fix Audio Channels in Video Proxies
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

📦 Download
Releases
Prebuilt .app available (signed + zipped)

🧠 Created By
Colm Moore @thisiscolm www.colmmoore.com

