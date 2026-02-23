# Simple Windows GUI for yt-dlp (Python/Tkinter)

This repository now includes a minimal GUI wrapper at `yt_dlp_gui.py` to expose common `yt-dlp` options visually.

## Run

From the repository root:

```bash
python yt_dlp_gui.py
```

## Current features

- URL input
- Destination folder picker
- Filename template (`-o`) and format selector (`-f`)
- Audio-only mode (extract to mp3)
- Playlist on/off toggle
- Embed subtitles toggle
- Write thumbnail toggle
- Browser cookies selector (`--cookies-from-browser`)
- Custom free-form argument input
- Command preview
- Live download log and stop button

## Notes

- The GUI runs `yt-dlp` using: `python -m yt_dlp`.
- It is intentionally minimal and meant as a base for iterative enhancement.
- `Custom arguments` are split by shell-like spaces; quoted values are supported.
