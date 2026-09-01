# Task 01: Image Spatial & EXIF Metadata Analyzer

**Author:** Rudranshpardeshi09  
**Module:** Digital Image Analysis & Properties

---

## 🎯 Overview
This task analyzes raster image files, extracting essential spatial resolution parameters, color depth, megapixels, dimensions, aspect ratio, and embedded camera EXIF metadata (Make, Model, Date Taken, Orientation, Software).

## 📁 Directory Structure
```text
task-01-image-analyser/
├── README.md                           # Task documentation
├── image_analyser.py                   # Core analyzer script
└── outputs/                            # Execution screenshots & sample outputs
    └── image_processing_output.png
```

## 🚀 Execution Guide

### 1. Default Sample Image:
```bash
python task-01-image-analyser/image_analyser.py
```
*(Automatically resolves `datasets/images/flower.jpg`)*

### 2. Custom Image File:
```bash
python task-01-image-analyser/image_analyser.py --file datasets/images/flower2.jpg
```
