# yt-dlp Studio (Modern Windows GUI)

This repository includes a modern GUI wrapper at `yt_dlp_gui.py` focused on a cleaner, more professional UX.

## Run

From the repository root:

```bash
python yt_dlp_gui.py
```

## UX highlights

- Modern two-column dashboard layout
- Card-style sections (glass-like look)
- Theme switcher (`dark` / `light`)
- Higher-contrast selected values in mode/quality/theme selectors
- Accent action buttons and styled progress bar
- Live command preview and download logs

## Features

- Multi-URL input (one URL per line)
- URL box supports right-click context menu and a dedicated `Paste` button
- Presets (`custom`, `best-video`, `audio-mp3`, `subtitles-only`, `thumbnail-only`)
- Destination picker and filename template
- Quality selectors:
  - Download mode (`video+audio`, `video-only`, `audio-only`)
  - Video quality (`best`, `2160p`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `worst`)
  - Audio quality (`best`, `320k`, `256k`, `192k`, `160k`, `128k`, `96k`, `worst`)
  - Audio format (`mp3`, `m4a`, `aac`, `opus`, `vorbis`, `wav`)
- Optional manual `-f` expression override
- Playlist/subtitle/thumbnail toggles
- Browser cookies option (`--cookies-from-browser`)
- Custom argument input
- Save/load defaults to `~/.yt_dlp_gui_config.json`

## Notes

- The GUI runs `yt-dlp` using: `python -m yt_dlp`.
- The quality dropdowns auto-build `-f` unless manual override is enabled.
- Theme selection is persisted in the defaults config.
