# Audio A/B Tester

A simple Python GUI tool to compare (A/B test) two audio files side-by-side.  
Supports WAV and MP3, shows waveform, and allows Play, Pause, and Stop.

---

## Features

- Load two audio files (Audio File 1 vs Audio File 2)  
- Display waveform with live playback progress  
- Play, Pause, Stop controls  
- Metadata display (duration, channels, sample rate)  

---

## Screenshots

![Main Window](icons/audio-ab-tester-1.png)  
![Waveform View](icons/audio-ab-tester-2.png)  

---

## Requirements

- Python 3.8+  
- Dependencies listed in `requirements.txt`  

---

## Installation

```bash
# Clone the repository
git clone https://github.com/hamidahang/audio-ab-tester.git
cd audio-ab-tester

# Install dependencies
pip install -r requirements.txt

# Run the program
python src/audio-ab-tester.py

