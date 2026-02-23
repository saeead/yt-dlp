# Saeid YT Downloader Pro (Modern Windows GUI)

This repository includes a redesigned GUI at `yt_dlp_gui.py` with a more premium, design-system-inspired experience.

## Run

From the repository root:

```bash
python yt_dlp_gui.py
```

## UI/UX highlights

- Modern dashboard layout with clean visual hierarchy
- Card-based sections with glass-like aesthetic and soft contrast
- Live theme switching (`dark` / `light`)
- High-contrast selected values in dropdowns for better readability
- Dedicated URL `Paste` button + right-click context menu Paste
- App window title renamed to `Saeid YT Downloader Pro`
- Uses repository icon (`devscripts/logo.ico`) when available
- Styled action buttons, command preview, progress, and log panel

## Features

- Multi-URL input (one URL per line)
- Presets (`custom`, `best-video`, `audio-mp3`, `subtitles-only`, `thumbnail-only`)
- Destination picker and filename template
- Quality controls:
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
- Theme choice is persisted in config defaults.
- Quality selectors auto-build `-f` when manual override is disabled.
