# Multimedia Systems Laboratory

[![Author](https://img.shields.io/badge/Author-Rudranshpardeshi09-blue.svg)](https://github.com/Rudranshpardeshi09)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey.svg)]()

A clean, modular multimedia processing laboratory repository featuring implementations for **Image Spatial & EXIF Metadata Analysis**, **Video Stream Demuxing & Container Inspection**, and **Audio Signal & ID3 Stream Analysis**.

---

## 📑 Table of Contents
- [Architecture & Repository Structure](#-architecture--repository-structure)
- [Core Lab Tasks](#-core-lab-tasks)
- [Prerequisites & Setup](#-prerequisites--setup)
- [Quick Start & Execution](#-quick-start--execution)
- [Datasets Catalog](#-datasets-catalog)
- [Git Workflow (Push under your profile)](#-git-workflow)
- [Author](#-author)

---

## 📂 Architecture & Repository Structure

```text
multimedia-lab/
├── .gitignore                          # Clean production Git ignore
├── README.md                           # Master laboratory documentation
├── requirements.txt                    # Project dependencies
├── main.py                             # Central CLI task runner
│
├── task-01-image-analyser/             # 🖼️ Task 1: Image Spatial & EXIF Metadata Analyzer
│   ├── README.md
│   ├── image_analyser.py
│   └── outputs/
│       └── image_processing_output.png
│
├── task-02-video-analyser/             # 🎥 Task 2: Video Stream Demuxer & Metadata Analyzer
│   ├── README.md
│   ├── video_analyser.py
│   └── outputs/
│       └── video_processing.png
│
├── task-03-audio-analyser/             # 🎵 Task 3: Audio Signal & Stream Properties Analyzer
│   ├── README.md
│   ├── audio_analyser.py
│   └── outputs/
│       └── audio_processing.png
│
├── datasets/                           # 🗂️ Categorized Media Assets
│   ├── README.md
│   ├── images/                         # flower.jpg, flower2.jpg
│   ├── audio/                          # Afternoon_Window.mp3
│   └── video/                          # voiceover.mp4
│
└── tools/                              # 🛠️ Environment Diagnostics (env_checker.py)
    └── env_checker.py
```

---

## 🎯 Core Lab Tasks

### 🖼️ Task 1: Image Spatial & EXIF Metadata Analyzer
- **Folder:** [`task-01-image-analyser/`](file:///c:/Users/rudra/Desktop/multimedia%20lab/task-01-image-analyser)
- **Script:** [`image_analyser.py`](file:///c:/Users/rudra/Desktop/multimedia%20lab/task-01-image-analyser/image_analyser.py)
- **Capabilities:** Analyzes format, resolution (DPI), dimensions, megapixels, aspect ratios, color bands, and embedded EXIF tags.
- **Run:**
  ```bash
  python task-01-image-analyser/image_analyser.py
  # With custom image:
  python task-01-image-analyser/image_analyser.py --file datasets/images/flower2.jpg
  ```

---

### 🎥 Task 2: Video Stream Demuxer & Analyzer
- **Folder:** [`task-02-video-analyser/`](file:///c:/Users/rudra/Desktop/multimedia%20lab/task-02-video-analyser)
- **Script:** [`video_analyser.py`](file:///c:/Users/rudra/Desktop/multimedia%20lab/task-02-video-analyser/video_analyser.py)
- **Capabilities:** Interrogates video containers, decodes video/audio streams, calculates frame rate (FPS), resolutions, bitrates, and pixel formats.
- **Run:**
  ```bash
  python task-02-video-analyser/video_analyser.py
  # With custom video:
  python task-02-video-analyser/video_analyser.py --file datasets/video/voiceover.mp4
  ```

---

### 🎵 Task 3: Audio Signal & Stream Analyzer
- **Folder:** [`task-03-audio-analyser/`](file:///c:/Users/rudra/Desktop/multimedia%20lab/task-03-audio-analyser)
- **Script:** [`audio_analyser.py`](file:///c:/Users/rudra/Desktop/multimedia%20lab/task-03-audio-analyser/audio_analyser.py)
- **Capabilities:** Extracts audio sampling frequencies, channel layouts, stream bitrates, sample formats, and ID3/Vorbis tags.
- **Run:**
  ```bash
  python task-03-audio-analyser/audio_analyser.py
  # With custom audio:
  python task-03-audio-analyser/audio_analyser.py --file datasets/audio/Afternoon_Window.mp3
  ```

---

## ⚙️ Prerequisites & Setup

```bash
# 1. Virtual environment setup (Recommended)
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux / macOS: source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify environment
python tools/env_checker.py
```

---

## 🚀 Quick Start & Execution

Launch any task or run all tasks using the central CLI runner:

```bash
# Interactive Selection Menu:
python main.py

# Direct Task Commands:
python main.py -t 1      # Run Task 1 (Image Analyzer)
python main.py -t 2      # Run Task 2 (Video Analyzer)
python main.py -t 3      # Run Task 3 (Audio Analyzer)
python main.py -t d      # Run Diagnostics (env_checker.py)
python main.py -t all    # Run all tasks & diagnostics in sequence
```

---

## 🗂️ Datasets Catalog

Categorized under [`datasets/`](file:///c:/Users/rudra/Desktop/multimedia%20lab/datasets):
- **`datasets/images/`**: `flower.jpg`, `flower2.jpg`
- **`datasets/audio/`**: `Afternoon_Window.mp3`
- **`datasets/video/`**: `voiceover.mp4`

---

## 🛠️ Git Workflow

```powershell
# 1. Stage & Commit Root Config and Tools
git add .gitignore requirements.txt README.md main.py tools
git commit -m "chore: setup clean task-based structure, tools, and documentation"

# 2. Stage & Commit Task 1 (Image Analyser) + Datasets
git add task-01-image-analyser datasets/images
git commit -m "feat(task-01): implement image spatial and EXIF metadata analyzer"

# 3. Stage & Commit Task 2 (Video Analyser) + Datasets
git add task-02-video-analyser datasets/video
git commit -m "feat(task-02): implement video container demuxer and stream analyzer"

# 4. Stage & Commit Task 3 (Audio Analyser) + Datasets
git add task-03-audio-analyser datasets/audio
git commit -m "feat(task-03): implement audio signal stream analyzer and ID3 tag parser"

# 5. Push to GitHub
git push origin main
```

---

## 👤 Author
**Rudransh Pardeshi**  
- GitHub: [@Rudranshpardeshi09](https://github.com/Rudranshpardeshi09)
- Email: `rudranshpardeshi12@gmail.com`
