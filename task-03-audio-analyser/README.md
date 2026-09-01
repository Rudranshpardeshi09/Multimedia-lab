# Task 03: Audio Signal & Stream Properties Analyzer

**Author:** Rudranshpardeshi09  
**Module:** Audio Processing & Stream Inspection

---

## 🎯 Overview
This task analyzes digital audio streams (MP3, WAV, AAC, FLAC, OGG), extracting sample rates, channel configurations (mono/stereo/surround), bitrates, sample formats, bits-per-sample, duration, and embedded ID3/Vorbis tags.

## 📁 Directory Structure
```text
task-03-audio-analyser/
├── README.md                           # Task documentation
├── audio_analyser.py                   # Core analyzer script
└── outputs/                            # Execution screenshots & sample outputs
    └── audio_processing.png
```

## 🚀 Execution Guide

### 1. Default Sample Audio:
```bash
python task-03-audio-analyser/audio_analyser.py
```
*(Automatically resolves `datasets/audio/Afternoon_Window.mp3`)*

### 2. Custom Audio File:
```bash
python task-03-audio-analyser/audio_analyser.py --file path/to/audio.mp3
```
