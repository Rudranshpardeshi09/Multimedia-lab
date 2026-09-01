# Task 02: Video Stream Demuxer & Metadata Analyzer

**Author:** Rudranshpardeshi09  
**Module:** Video Processing & Stream Multiplexing

---

## 🎯 Overview
This task interrogates video containers (MP4, MKV, AVI, etc.) using `FFprobe`, demuxing video and audio streams to analyze frame rates (FPS), spatial dimensions, aspect ratios, video/audio bitrates, pixel formats, and container timestamps.

## 📁 Directory Structure
```text
task-02-video-analyser/
├── README.md                           # Task documentation
├── video_analyser.py                   # Core analyzer script
└── outputs/                            # Execution screenshots & sample outputs
    └── video_processing.png
```

## 🚀 Execution Guide

### 1. Default Sample Video:
```bash
python task-02-video-analyser/video_analyser.py
```
*(Automatically resolves `datasets/video/voiceover.mp4`)*

### 2. Custom Video File:
```bash
python task-02-video-analyser/video_analyser.py --file path/to/video.mp4
```
