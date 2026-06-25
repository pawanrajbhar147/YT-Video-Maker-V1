YT Maker — voiceover + images → video
Drop your voiceover and images into two fixed folders, run one command, and get a finished video with crossfades. Pairing is automatic and a log is written every run so you can cross-check exactly what happened.

Folder layout
yt-maker/
├── config.json          # your settings (edit once)
├── make_video.py        # the only script you run
├── README.md
├── audio/               # ← drop your voiceover files here (one per beat)
├── images/              # ← drop your images here (one per beat)
├── working/             # scratch (auto-created)
└── output/
    ├── video.mp4        # the finished video (overwritten each run)
    └── logs/
        └── run_<timestamp>.log   # one log per run, kept for cross-checking
One-time setup
Install ffmpeg (you already have it via winget). If make_video.py can't find it, open config.json and set the full path, e.g. "ffmpeg": "C:\\Users\\<you>\\AppData\\Local\\Microsoft\\WinGet\\Links\\ffmpeg.exe". Leave it as "" to auto-detect.
That's it — no Python packages to install. Pure standard library + ffmpeg.
Make a video (every time)
Put your voiceover files in audio/ — one file per beat.

Put your images in images/ — one file per beat.

Run:

python make_video.py
Get output/video.mp4. Check output/logs/run_<timestamp>.log to see the exact image ↔ audio pairing for that run.

Making a new video? Just delete/replace the files in audio/ and images/ and run again. The new video.mp4 overwrites the old one (move it out first if you want to keep it). Logs are never overwritten — each run gets its own.

How pairing works
Files are matched by order: 1st image ↔ 1st audio, 2nd ↔ 2nd, and so on. Each image is shown for exactly the length of its paired voiceover file, with a crossfade into the next. Your files are never renamed or moved.

Images are ordered by filename (001_001.jpg < 002_002.jpg …).
Audio is ordered by the timestamp in the filename (e.g. the ... 5_41PM (2) that your TTS adds), so download order doesn't matter.
The log prints the full pairing every run — always glance at it to confirm beat 1's image lines up with beat 1's voiceover.

Settings (config.json)
Key	Meaning
ffmpeg	Full path to ffmpeg, or "" to auto-detect
width, height, fps	Output resolution and frame rate
transition	"crossfade" or "cut"
crossfade_seconds	Length of each dissolve
zoom	true = slow zoom-out on each image, false = static (keep false for now)
start_zoom, end_zoom	Zoom range when zoom is on
upscale	Zoom smoothness (2 = good, 1 = fastest)
audio_dir, image_dir	The fixed input folders
output	Path of the final video
audio_order	"fname_time" (default), "ctime", or "name"
image_order	"name" (default) or "ctime"
reverse_audio	Set true once if the log shows audio paired in reverse
Troubleshooting
COUNT MISMATCH — different number of images vs audio files. The log lists both so you can spot the missing/extra one. Fix the folder and rerun.
Audio paired in reverse — set "reverse_audio": true in config.json. Re-run and check the log pairing.
ffmpeg not found — set the full "ffmpeg" path in config.json.
An ffmpeg render error — the full ffmpeg message is written to the run log; open the latest file in output/logs/ to read it.
What's next (optional, later)
Turn on the slow zoom-out once it's finalized ("zoom": true).
Burn on-screen text / captions per beat.
Add a background music bed under the voiceover.