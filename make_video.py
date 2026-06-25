#!/usr/bin/env python3
"""
make_video.py — drop voiceover + images in the fixed folders, run, get a video.

  audio/   <- your voiceover files (one per beat, any names)
  images/  <- your images (one per beat, any names)
Run:  python make_video.py
Out:  output/video.mp4   +   output/logs/run_<timestamp>.log

Pairing is by order: 1st image <- 1st audio, etc. The log prints the exact
pairing every run so you can cross-check. Files are never renamed or moved.
"""

import contextlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import wave
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
AUDIO_EXTS = (".wav", ".mp3", ".m4a")


def natural_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def fname_time(f):
    m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4}).*?(\d{1,2})_(\d{2})\s*([AP]M)", f)
    suf = re.search(r"\((\d+)\)", f)
    n = int(suf.group(1)) if suf else 0
    if not m:
        return (datetime.max, n, natural_key(f))
    dt = datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}{m.group(4)}",
                           "%B %d, %Y %I:%M%p")
    return (dt, n, natural_key(f))


def list_sorted(folder, exts, order, reverse):
    files = [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]
    if order == "name":
        files.sort(key=natural_key)
    elif order == "ctime":
        files.sort(key=lambda f: os.path.getctime(os.path.join(folder, f)))
    else:
        files.sort(key=fname_time)
    if reverse:
        files.reverse()
    return [os.path.join(folder, f) for f in files]


def resolve_ffmpeg(override):
    for c in (override, "ffmpeg",
              os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe")):
        if c and (shutil.which(c) or os.path.isfile(c)):
            return c
    sys.exit("ffmpeg not found — set 'ffmpeg' to its full path in config.json")


def duration(path):
    if path.lower().endswith(".wav"):
        with contextlib.closing(wave.open(path, "rb")) as w:
            return w.getnframes() / float(w.getframerate())
    raise SystemExit(f"Only .wav is supported right now (got {path}).")


def run(cmd, log):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log.error("FFMPEG FAILED:\n" + (r.stderr or "")[-2000:])
        sys.exit(1)
    return r


def setup_log(out_video):
    logs = os.path.join(os.path.dirname(out_video) or ".", "logs")
    os.makedirs(logs, exist_ok=True)
    path = os.path.join(logs, f"run_{datetime.now():%Y-%m-%d_%H-%M-%S}.log")
    log = logging.getLogger("ytmaker")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(fh); log.addHandler(ch)
    return log, path


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
    W, H, FPS = cfg.get("width", 1920), cfg.get("height", 1080), cfg.get("fps", 30)
    T = float(cfg.get("crossfade_seconds", 0.5))
    transition = cfg.get("transition", "crossfade")
    ZOOM = cfg.get("zoom", False)
    SZ, EZ, UP = cfg.get("start_zoom", 1.08), cfg.get("end_zoom", 1.0), cfg.get("upscale", 2)
    out_video = os.path.join(ROOT, cfg.get("output", "output/video.mp4"))
    adir = os.path.join(ROOT, cfg.get("audio_dir", "audio"))
    idir = os.path.join(ROOT, cfg.get("image_dir", "images"))
    work = os.path.join(ROOT, "working")
    for d in (adir, idir, os.path.dirname(out_video), work):
        os.makedirs(d or ".", exist_ok=True)

    log, log_path = setup_log(out_video)
    log.info("=" * 60)
    log.info(f"RUN {datetime.now():%Y-%m-%d %H:%M:%S}")
    FFMPEG = resolve_ffmpeg(cfg.get("ffmpeg", ""))
    log.info(f"ffmpeg: {FFMPEG}")

    images = list_sorted(idir, IMAGE_EXTS, cfg.get("image_order", "name"), False)
    audios = list_sorted(adir, AUDIO_EXTS, cfg.get("audio_order", "fname_time"),
                         cfg.get("reverse_audio", False))

    if not images or not audios:
        log.error("No files found. Put images in images/ and voiceover in audio/, then rerun.")
        sys.exit(1)
    if len(images) != len(audios):
        log.error(f"COUNT MISMATCH: {len(images)} images vs {len(audios)} audio files.")
        log.error("Images: " + ", ".join(os.path.basename(i) for i in images))
        log.error("Audio : " + ", ".join(os.path.basename(a) for a in audios))
        sys.exit(1)

    durs = [duration(a) for a in audios]
    N = len(images)
    log.info(f"{N} beats · voiceover {sum(durs):.1f}s · transition={transition} · zoom={ZOOM}")
    log.info("Pairing (beat: image  <-  audio  =  seconds):")
    for i in range(N):
        log.info(f"  {i+1:02d}: {os.path.basename(images[i])}  <-  "
                 f"{os.path.basename(audios[i])}  =  {durs[i]:.2f}s")

    # 1) continuous voiceover
    alist = os.path.join(work, "audio.txt")
    with open(alist, "w", encoding="utf-8") as f:
        for a in audios:
            f.write(f"file '{os.path.abspath(a)}'\n")
    voice = os.path.join(work, "voiceover.wav")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", alist,
         "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", voice], log)

    BW, BH = int(W * UP) & ~1, int(H * UP) & ~1
    def zoom(D):
        Z = f"({SZ}-({SZ}-{EZ})*t/{D:.3f})"
        return f",scale={BW}:{BH},crop=w=iw/{Z}:h=ih/{Z}:x=(iw-ow)/2:y=(ih-oh)/2,scale={W}:{H}"

    # 2) picture track
    if transition == "crossfade" and N > 1:
        SLACK = 1.0
        hold = [durs[i] + T + SLACK for i in range(N)]
        inputs = []
        for i in range(N):
            inputs += ["-loop", "1", "-t", f"{hold[i]:.3f}", "-i", images[i]]
        inputs += ["-i", voice]; aidx = N
        fc = []
        for i in range(N):
            c = (f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                 f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
            if ZOOM:
                c += zoom(hold[i])
            c += f",setsar=1,fps={FPS},format=yuv420p[v{i}]"
            fc.append(c)
        acc, prev = 0.0, "[v0]"
        for i in range(N - 1):
            acc += durs[i]
            o = f"[x{i}]"
            fc.append(f"{prev}[v{i+1}]xfade=transition=fade:duration={T}:offset={acc:.3f}{o}")
            prev = o
        run([FFMPEG, "-y", *inputs, "-filter_complex", ";".join(fc),
             "-map", prev, "-map", f"{aidx}:a",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_video], log)
    else:
        clips = []
        for i in range(N):
            clip = os.path.join(work, f"c{i:03d}.mp4")
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                  f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
            if ZOOM:
                vf += zoom(durs[i])
            vf += ",setsar=1,format=yuv420p"
            run([FFMPEG, "-y", "-loop", "1", "-t", f"{durs[i]:.3f}", "-i", images[i],
                 "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "20", "-pix_fmt", "yuv420p", clip], log)
            clips.append(clip)
        vlist = os.path.join(work, "video.txt")
        with open(vlist, "w") as f:
            for c in clips:
                f.write(f"file '{os.path.abspath(c)}'\n")
        silent = os.path.join(work, "silent.mp4")
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", vlist, "-c", "copy", silent], log)
        run([FFMPEG, "-y", "-i", silent, "-i", voice, "-c:v", "copy", "-c:a", "aac",
             "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_video], log)

    log.info(f"DONE -> {out_video}")
    log.info(f"Log saved -> {log_path}")


if __name__ == "__main__":
    main()