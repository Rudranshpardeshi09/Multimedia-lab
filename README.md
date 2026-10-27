# Multimedia Systems Lab

Lab tasks on image, video and audio, by [Rudranshpardeshi09](https://github.com/Rudranshpardeshi09).

## Setup

```powershell
pip install -r requirements.txt
$env:PATH = "$PWD\tools\ffmpeg\bin;$env:PATH"
```

Run any task with `python main.py`.

## Task 1: Image Analyser

Reads an image's size, DPI and EXIF info.

```powershell
python task-01-image-analyser/image_analyser.py
```

![Task 1 output](task-01-image-analyser/outputs/task-01-image-analysis.png)

## Task 2: Video Analyser

Reads a video's codec, resolution, FPS and audio.

```powershell
python task-02-video-analyser/video_analyser.py
```

![Task 2 output](task-02-video-analyser/outputs/task-02-video-analysis.png)

## Task 3: Audio Analyser

Reads an audio file's codec, sample rate and channels.

```powershell
python task-03-audio-analyser/audio_analyser.py
```

![Task 3 output](task-03-audio-analyser/outputs/task-03-audio-analysis.png)

## Task 4: Voice Transformer

Says what you speak back in a different AI voice.

Put your ElevenLabs key in `task-04-voice-transformer/.env` (copy `.env.example`), then:

```powershell
python task-04-voice-transformer/voice_transformer.py --serve
```

Open http://127.0.0.1:5000. Click the image to watch the demo:

[![Task 4 demo](task-04-voice-transformer/outputs/task-04-demo.png)](task-04-voice-transformer/outputs/task-04-demo.mp4)

## Task 5: Image Enhancement

Enhances an image and saves the results.

```powershell
python task-05-image-enhancement/image_enhancer.py
```

![Task 5 output](task-05-image-enhancement/outputs/testimage/before_after.png)

Tasks 1, 2, 3 and 5 use the file in their `input/` folder; add `--file path` to use another one.
