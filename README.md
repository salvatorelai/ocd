# O'Reilly Video Course Downloader 🎓

A powerful Python tool to download **complete O'Reilly Learning courses** with videos and transcripts, automatically organized by chapters.

> **Note**: This tool is designed specifically for downloading complete video course.

## Features ✨

- **📚 Complete Course Downloads**: Download entire courses with all modules and lessons
- **🎥 Video Downloads**: High-quality video downloads via HLS/m3u8 streams
- **📝 Transcript Extraction**: Extract video transcripts with timestamps
- **� Smart Organization**: Automatically organize by Module → Lesson → Videos
- **🔄 Resume Support**: Continue interrupted downloads
- **🚀 Headless Mode**: Run without browser window
- **⚡ Transcript-Only Mode**: Download just transcripts (10x faster, 1000x less storage)
- **💾 Persistent Login**: Chrome profile saves login permanently
- **🎯 Progress Tracking**: Visual feedback with animated spinner

## Quick Start 🚀

### Installation

```bash
# Install dependencies
pip install selenium

# Install FFmpeg (for video download)
choco install ffmpeg  # Windows
# or brew install ffmpeg  # macOS
```

### Usage

#### One Simple Command to Download Complete Course

```bash
# Download complete course (videos + transcripts)
python oreilly_course_downloader.py \
  --url "https://learning.oreilly.com/course/aws-certified-cloud/9780138314934/" \
  --email "your@email.com" \
  --password "yourpassword"

# Transcripts only (10x faster, 1000x less storage)
python oreilly_course_downloader.py \
  --url "https://learning.oreilly.com/course/aws-certified-cloud/9780138314934/" \
  --email "your@email.com" \
  --password "yourpassword" \
  --transcript-only

# Custom course name
python oreilly_course_downloader.py \
  --url "COURSE_URL" \
  --name "My Course Name" \
  --email "your@email.com" \
  --password "yourpassword"
```

> **Note**: Course structure extraction happens automatically in the background. No manual steps needed!

## Project Structure 📁

```
oreilly-downloader/
├── oreilly_base_downloader.py          # Base class with core functionality
├── oreilly_course_downloader.py        # Main course downloader (USE THIS)
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── chrome_profile/                     # Persistent Chrome profile
├── downloads/                          # Downloaded content
│   └── Course Name/
│       ├── 01 - Module 1/
│       │   └── 01 - Lesson 1/
│       │       ├── video1.mp4
│       │       └── video1_transcript.txt
└── *.json                              # Course structure files
```


**Benefits of Transcript-Only:**
- ⚡ 10x faster download
- 💾 1000x less storage
- 🔍 Easy to search and analyze
- 🤖 AI-friendly text format

### Custom Course Name

```bash
# Specify custom folder name
python oreilly_course_downloader.py \
  --url "https://learning.oreilly.com/course/python-fundamentals/9780138312817/" \
  --name "Python Fundamentals 2024" \
  --email "your@email.com" \
  --password "yourpassword"
```

### Show Browser Window (Debugging)

```bash
# Run with visible browser (useful for debugging)
python oreilly_course_downloader.py \
  --url "COURSE_URL" \
  --email "your@email.com" \
  --password "yourpassword" \
  --no-headless
```

> **Note**: By default, browser runs in headless mode (no window). Use `--no-headless` to see the browser.

**Benefits of Transcript-Only:**
- ⚡ 10x faster download
- 💾 1000x less storage
- 🔍 Easy to search and analyze
- 🤖 AI-friendly text format

## Configuration ⚙️


### Reset Login

```bash
python oreilly_course_downloader.py --reset-profile
```



## Troubleshooting 🔧

### Chrome Profile Issues
```bash
# Reset Chrome profile to force re-login
python oreilly_course_downloader.py --reset-profile
```

### FFmpeg Not Found
```bash
# Windows
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### Login Issues
- Make sure credentials are correct
- Try resetting Chrome profile
- Check if O'Reilly account is active

## Performance 📊

| Operation | Normal Mode | Transcript-Only | Speedup |
|-----------|-------------|-----------------|---------|
| Single Video | ~30 seconds | ~3 seconds | **10x** |
| 100 Videos | ~50 minutes | ~5 minutes | **10x** |
| Storage | ~1-5 GB | ~1-5 MB | **1000x** |


## Requirements 📋

- Python 3.7+
- Selenium 4.15.0+
- FFmpeg (for video downloads)
- Chrome/Chromium browser
- Active O'Reilly Learning account



## Contributing 🤝

Contributions are welcome! Feel free to:
- Report bugs via GitHub Issues
- Suggest features
- Submit pull requests
- Improve documentation

## Disclaimer ⚠️

This tool is for **educational purposes and personal use only**. Users are responsible for complying with O'Reilly Media's Terms of Service. Please respect copyright and intellectual property rights.

## License 📄

MIT License - see [LICENSE](LICENSE) file for details.

## Credits 👏

Built with ❤️ for efficient learning and offline access.

**Technologies Used:**
- Python 3.7+
- Selenium WebDriver
- Chrome DevTools Protocol
- FFmpeg

---

**⭐ If you find this useful, please star the repo!**

