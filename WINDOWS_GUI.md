# Simple Windows GUI for yt-dlp (Python/Tkinter)

This repository includes an enhanced GUI wrapper at `yt_dlp_gui.py` to expose common `yt-dlp` options visually.

## Run

From the repository root:

```bash
python yt_dlp_gui.py
```

## Current features

- Multi-URL input (one URL per line)
- Presets (`best-video`, `audio-mp3`, `subtitles-only`, `thumbnail-only`)
- Destination folder picker
- Filename template (`-o`)
- Quality selectors:
  - Download mode (`video+audio`, `video-only`, `audio-only`)
  - Video quality (`best`, `2160p`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `worst`)
  - Audio quality (`best`, `320k`, `256k`, `192k`, `160k`, `128k`, `96k`, `worst`)
  - Audio format for audio-only mode (`mp3`, `m4a`, `aac`, `opus`, `vorbis`, `wav`)
- Optional manual format override (`-f`) for advanced users
- Playlist on/off toggle
- Embed subtitles toggle
- Write thumbnail toggle
- Browser cookies selector (`--cookies-from-browser`)
- Custom free-form argument input
- Windows-style command preview
- Live download log
- Parsed download percentage progress bar
- Stop button
- Save/load default UI settings to `~/.yt_dlp_gui_config.json`

## Notes

- The GUI runs `yt-dlp` using: `python -m yt_dlp`.
- Quality dropdowns auto-generate the `-f` format expression unless manual format override is enabled.
- `Custom arguments` are parsed using `shlex.split(..., posix=False)`.
