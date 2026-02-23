#!/usr/bin/env python3
"""Enhanced Tkinter-based GUI for yt-dlp on Windows."""

from __future__ import annotations

import json
import queue
import re
import shlex
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

DOWNLOAD_PROGRESS_RE = re.compile(r"\[download\]\s+(\d{1,3}(?:\.\d+)?)%")
CONFIG_PATH = Path.home() / '.yt_dlp_gui_config.json'

VIDEO_HEIGHT_MAP = {
    'best': None,
    '2160p': 2160,
    '1440p': 1440,
    '1080p': 1080,
    '720p': 720,
    '480p': 480,
    '360p': 360,
    'worst': 'worst',
}

AUDIO_ABR_MAP = {
    'best': None,
    '320k': 320,
    '256k': 256,
    '192k': 192,
    '160k': 160,
    '128k': 128,
    '96k': 96,
    'worst': 'worst',
}


class YtDlpGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('yt-dlp Simple GUI')
        self.root.geometry('980x780')
        self.root.minsize(820, 600)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()

        self.dest_var = tk.StringVar(value=str(Path.cwd()))
        self.filename_var = tk.StringVar(value='%(title)s.%(ext)s')
        self.format_var = tk.StringVar(value='bestvideo+bestaudio/best')
        self.manual_format_var = tk.BooleanVar(value=False)

        self.media_mode_var = tk.StringVar(value='video+audio')
        self.video_quality_var = tk.StringVar(value='1080p')
        self.audio_quality_var = tk.StringVar(value='192k')
        self.audio_format_var = tk.StringVar(value='mp3')

        self.playlist_var = tk.BooleanVar(value=False)
        self.embed_subs_var = tk.BooleanVar(value=False)
        self.write_thumbnail_var = tk.BooleanVar(value=False)
        self.cookies_browser_var = tk.StringVar(value='')
        self.custom_args_var = tk.StringVar()
        self.preset_var = tk.StringVar(value='custom')
        self.status_var = tk.StringVar(value='Ready')

        self._build_ui()
        self._load_config()
        self.root.after(120, self._poll_output_queue)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill='both', expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(14, weight=1)

        ttk.Label(main, text='Preset:').grid(row=0, column=0, sticky='w', pady=(0, 6))
        preset_frame = ttk.Frame(main)
        preset_frame.grid(row=0, column=1, sticky='ew', pady=(0, 6))
        preset_frame.columnconfigure(0, weight=1)
        self.preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            state='readonly',
            values=['custom', 'best-video', 'audio-mp3', 'subtitles-only', 'thumbnail-only'],
        )
        self.preset_combo.grid(row=0, column=0, sticky='ew')
        self.preset_combo.bind('<<ComboboxSelected>>', self._apply_preset)
        ttk.Button(preset_frame, text='Save as defaults', command=self._save_config).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(main, text='URLs (one per line):').grid(row=1, column=0, sticky='nw', pady=(0, 6))
        self.urls_text = tk.Text(main, height=4, wrap='word')
        self.urls_text.grid(row=1, column=1, sticky='ew', pady=(0, 6))
        self.urls_text.bind('<KeyRelease>', lambda *_: self.update_preview())

        ttk.Label(main, text='Destination folder:').grid(row=2, column=0, sticky='w', pady=(0, 6))
        dest_frame = ttk.Frame(main)
        dest_frame.grid(row=2, column=1, sticky='ew', pady=(0, 6))
        dest_frame.columnconfigure(0, weight=1)
        ttk.Entry(dest_frame, textvariable=self.dest_var).grid(row=0, column=0, sticky='ew')
        ttk.Button(dest_frame, text='Browse', command=self._browse_dest).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(main, text='Filename template (-o):').grid(row=3, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(main, textvariable=self.filename_var).grid(row=3, column=1, sticky='ew', pady=(0, 6))

        quality_frame = ttk.LabelFrame(main, text='Quality selection', padding=10)
        quality_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(8, 6))
        quality_frame.columnconfigure(1, weight=1)
        quality_frame.columnconfigure(3, weight=1)

        ttk.Label(quality_frame, text='Download mode:').grid(row=0, column=0, sticky='w', pady=2)
        ttk.Combobox(
            quality_frame,
            textvariable=self.media_mode_var,
            state='readonly',
            values=['video+audio', 'video-only', 'audio-only'],
        ).grid(row=0, column=1, sticky='ew', padx=(6, 12), pady=2)

        ttk.Label(quality_frame, text='Video quality:').grid(row=0, column=2, sticky='w', pady=2)
        ttk.Combobox(
            quality_frame,
            textvariable=self.video_quality_var,
            state='readonly',
            values=list(VIDEO_HEIGHT_MAP.keys()),
        ).grid(row=0, column=3, sticky='ew', padx=(6, 0), pady=2)

        ttk.Label(quality_frame, text='Audio quality:').grid(row=1, column=0, sticky='w', pady=2)
        ttk.Combobox(
            quality_frame,
            textvariable=self.audio_quality_var,
            state='readonly',
            values=list(AUDIO_ABR_MAP.keys()),
        ).grid(row=1, column=1, sticky='ew', padx=(6, 12), pady=2)

        ttk.Label(quality_frame, text='Audio format:').grid(row=1, column=2, sticky='w', pady=2)
        ttk.Combobox(
            quality_frame,
            textvariable=self.audio_format_var,
            state='readonly',
            values=['mp3', 'm4a', 'aac', 'opus', 'vorbis', 'wav'],
        ).grid(row=1, column=3, sticky='ew', padx=(6, 0), pady=2)

        manual_frame = ttk.Frame(main)
        manual_frame.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        manual_frame.columnconfigure(1, weight=1)
        ttk.Checkbutton(manual_frame, text='Use manual format expression (-f)', variable=self.manual_format_var).grid(
            row=0, column=0, sticky='w', padx=(0, 8)
        )
        ttk.Entry(manual_frame, textvariable=self.format_var).grid(row=0, column=1, sticky='ew')

        options = ttk.LabelFrame(main, text='Common options', padding=10)
        options.grid(row=6, column=0, columnspan=2, sticky='ew', pady=(8, 6))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)

        ttk.Checkbutton(options, text='Download playlist', variable=self.playlist_var).grid(
            row=0, column=0, sticky='w', padx=(0, 12), pady=2
        )
        ttk.Checkbutton(options, text='Embed subtitles', variable=self.embed_subs_var).grid(
            row=0, column=1, sticky='w', pady=2
        )
        ttk.Checkbutton(options, text='Write thumbnail', variable=self.write_thumbnail_var).grid(
            row=1, column=0, sticky='w', padx=(0, 12), pady=2
        )

        ttk.Label(main, text='Cookies from browser:').grid(row=7, column=0, sticky='w', pady=(0, 6))
        ttk.Combobox(
            main,
            textvariable=self.cookies_browser_var,
            state='readonly',
            values=['', 'chrome', 'firefox', 'edge', 'brave', 'opera', 'vivaldi'],
        ).grid(row=7, column=1, sticky='ew', pady=(0, 6))

        ttk.Label(main, text='Custom arguments:').grid(row=8, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(main, textvariable=self.custom_args_var).grid(row=8, column=1, sticky='ew', pady=(0, 6))

        command_frame = ttk.LabelFrame(main, text='Generated command preview', padding=10)
        command_frame.grid(row=9, column=0, columnspan=2, sticky='ew', pady=(8, 6))
        command_frame.columnconfigure(0, weight=1)
        self.command_preview = tk.Text(command_frame, height=3, wrap='word')
        self.command_preview.grid(row=0, column=0, sticky='ew')
        self.command_preview.configure(state='disabled')

        buttons = ttk.Frame(main)
        buttons.grid(row=10, column=0, columnspan=2, sticky='ew', pady=(8, 6))
        for col in range(4):
            buttons.columnconfigure(col, weight=1)

        self.run_button = ttk.Button(buttons, text='Start Download', command=self.start_download)
        self.run_button.grid(row=0, column=0, sticky='ew', padx=(0, 6))
        self.stop_button = ttk.Button(buttons, text='Stop', command=self.stop_download, state='disabled')
        self.stop_button.grid(row=0, column=1, sticky='ew', padx=6)
        ttk.Button(buttons, text='Clear Log', command=self.clear_log).grid(row=0, column=2, sticky='ew', padx=6)
        ttk.Button(buttons, text='Reset to default', command=self._reset_fields).grid(row=0, column=3, sticky='ew', padx=(6, 0))

        self.progress = ttk.Progressbar(main, mode='determinate', maximum=100)
        self.progress.grid(row=11, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        ttk.Label(main, textvariable=self.status_var).grid(row=12, column=0, columnspan=2, sticky='w', pady=(0, 4))

        ttk.Label(main, text='Output log:').grid(row=13, column=0, sticky='nw', pady=(0, 6))
        self.log_text = tk.Text(main, wrap='word')
        self.log_text.grid(row=14, column=0, columnspan=2, sticky='nsew')

        for variable in (
            self.dest_var,
            self.filename_var,
            self.format_var,
            self.manual_format_var,
            self.media_mode_var,
            self.video_quality_var,
            self.audio_quality_var,
            self.audio_format_var,
            self.playlist_var,
            self.embed_subs_var,
            self.write_thumbnail_var,
            self.cookies_browser_var,
            self.custom_args_var,
        ):
            variable.trace_add('write', lambda *_: self.update_preview())

        self.update_preview()

    def _get_urls(self) -> list[str]:
        return [line.strip() for line in self.urls_text.get('1.0', tk.END).splitlines() if line.strip()]

    def _browse_dest(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.dest_var.get() or str(Path.cwd()))
        if selected:
            self.dest_var.set(selected)

    def _reset_fields(self) -> None:
        self.preset_var.set('custom')
        self.urls_text.delete('1.0', tk.END)
        self.dest_var.set(str(Path.cwd()))
        self.filename_var.set('%(title)s.%(ext)s')
        self.manual_format_var.set(False)
        self.format_var.set('bestvideo+bestaudio/best')
        self.media_mode_var.set('video+audio')
        self.video_quality_var.set('1080p')
        self.audio_quality_var.set('192k')
        self.audio_format_var.set('mp3')
        self.playlist_var.set(False)
        self.embed_subs_var.set(False)
        self.write_thumbnail_var.set(False)
        self.cookies_browser_var.set('')
        self.custom_args_var.set('')
        self.progress['value'] = 0
        self.status_var.set('Ready')
        self.update_preview()

    def _apply_preset(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        preset = self.preset_var.get()
        self.manual_format_var.set(False)
        self.embed_subs_var.set(False)
        self.write_thumbnail_var.set(False)
        self.custom_args_var.set('')
        self.media_mode_var.set('video+audio')

        if preset == 'audio-mp3':
            self.media_mode_var.set('audio-only')
            self.audio_format_var.set('mp3')
            self.audio_quality_var.set('192k')
        elif preset == 'subtitles-only':
            self.custom_args_var.set('--skip-download --write-subs --sub-langs all')
        elif preset == 'thumbnail-only':
            self.custom_args_var.set('--skip-download --write-thumbnail')
        elif preset == 'best-video':
            self.video_quality_var.set('best')
            self.audio_quality_var.set('best')

        self.update_preview()

    def _save_config(self) -> None:
        data = {
            'dest': self.dest_var.get(),
            'filename': self.filename_var.get(),
            'manual_format': self.manual_format_var.get(),
            'format': self.format_var.get(),
            'media_mode': self.media_mode_var.get(),
            'video_quality': self.video_quality_var.get(),
            'audio_quality': self.audio_quality_var.get(),
            'audio_format': self.audio_format_var.get(),
            'playlist': self.playlist_var.get(),
            'embed_subs': self.embed_subs_var.get(),
            'write_thumbnail': self.write_thumbnail_var.get(),
            'cookies_browser': self.cookies_browser_var.get(),
            'custom_args': self.custom_args_var.get(),
            'preset': self.preset_var.get(),
        }
        try:
            CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding='utf-8')
            messagebox.showinfo('Saved', f'Default settings saved to:\n{CONFIG_PATH}')
        except OSError as err:
            messagebox.showerror('Save failed', f'Could not save settings:\n{err}')

    def _load_config(self) -> None:
        if not CONFIG_PATH.exists():
            return
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return

        self.dest_var.set(data.get('dest', self.dest_var.get()))
        self.filename_var.set(data.get('filename', self.filename_var.get()))
        self.manual_format_var.set(bool(data.get('manual_format', self.manual_format_var.get())))
        self.format_var.set(data.get('format', self.format_var.get()))
        self.media_mode_var.set(data.get('media_mode', self.media_mode_var.get()))
        self.video_quality_var.set(data.get('video_quality', self.video_quality_var.get()))
        self.audio_quality_var.set(data.get('audio_quality', self.audio_quality_var.get()))
        self.audio_format_var.set(data.get('audio_format', self.audio_format_var.get()))
        self.playlist_var.set(bool(data.get('playlist', self.playlist_var.get())))
        self.embed_subs_var.set(bool(data.get('embed_subs', self.embed_subs_var.get())))
        self.write_thumbnail_var.set(bool(data.get('write_thumbnail', self.write_thumbnail_var.get())))
        self.cookies_browser_var.set(data.get('cookies_browser', self.cookies_browser_var.get()))
        self.custom_args_var.set(data.get('custom_args', self.custom_args_var.get()))
        self.preset_var.set(data.get('preset', self.preset_var.get()))

    def _build_quality_format(self) -> str:
        mode = self.media_mode_var.get()
        video_choice = VIDEO_HEIGHT_MAP.get(self.video_quality_var.get(), 1080)
        audio_choice = AUDIO_ABR_MAP.get(self.audio_quality_var.get(), 192)

        if mode == 'video-only':
            if video_choice == 'worst':
                return 'worstvideo/worst'
            if video_choice is None:
                return 'bestvideo/best'
            return f'bestvideo[height<={video_choice}]/best[height<={video_choice}]'

        if mode == 'audio-only':
            if audio_choice == 'worst':
                return 'worstaudio/worst'
            if audio_choice is None:
                return 'bestaudio/best'
            return f'bestaudio[abr<={audio_choice}]/bestaudio/best'

        video_part = 'bestvideo' if video_choice is None else (
            'worstvideo' if video_choice == 'worst' else f'bestvideo[height<={video_choice}]'
        )
        audio_part = 'bestaudio' if audio_choice is None else (
            'worstaudio' if audio_choice == 'worst' else f'bestaudio[abr<={audio_choice}]'
        )
        return f'{video_part}+{audio_part}/best'

    def _build_base_command(self) -> list[str]:
        output_template = str(Path(self.dest_var.get()) / self.filename_var.get())
        command = [sys.executable, '-m', 'yt_dlp', '--newline', '-o', output_template]

        format_expr = self.format_var.get().strip() if self.manual_format_var.get() else self._build_quality_format()
        command.extend(['-f', format_expr])

        if self.media_mode_var.get() == 'audio-only':
            command.extend(['-x', '--audio-format', self.audio_format_var.get()])

        command.append('--yes-playlist' if self.playlist_var.get() else '--no-playlist')

        if self.embed_subs_var.get():
            command.extend(['--write-subs', '--embed-subs'])
        if self.write_thumbnail_var.get():
            command.extend(['--write-thumbnail', '--convert-thumbnails', 'jpg'])
        if self.cookies_browser_var.get():
            command.extend(['--cookies-from-browser', self.cookies_browser_var.get()])

        custom_args = self.custom_args_var.get().strip()
        if custom_args:
            command.extend(shlex.split(custom_args, posix=False))

        return command

    def build_command(self, include_urls: bool = True) -> list[str]:
        command = self._build_base_command()
        if include_urls:
            command.extend(self._get_urls())
        return command

    def update_preview(self) -> None:
        command = self.build_command(include_urls=False)
        preview = subprocess.list2cmdline(command + ['<URL ...>'])
        self.command_preview.configure(state='normal')
        self.command_preview.delete('1.0', tk.END)
        self.command_preview.insert('1.0', preview)
        self.command_preview.configure(state='disabled')

    def log(self, text: str) -> None:
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    def clear_log(self) -> None:
        self.log_text.delete('1.0', tk.END)

    def start_download(self) -> None:
        if self.process is not None:
            return

        urls = self._get_urls()
        if not urls:
            messagebox.showwarning('Missing URL', 'Please provide at least one URL (one per line).')
            return

        dest = Path(self.dest_var.get())
        if not dest.exists():
            messagebox.showwarning('Invalid destination', 'Destination folder does not exist.')
            return

        command = self.build_command(include_urls=True)
        self.log(f'Running: {subprocess.list2cmdline(command)}\n\n')

        self.run_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.status_var.set('Downloading...')
        self.progress['value'] = 0

        thread = threading.Thread(target=self._run_process, args=(command,), daemon=True)
        thread.start()

    def _run_process(self, command: list[str]) -> None:
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.output_queue.put(line)
            return_code = self.process.wait()
            self.output_queue.put(f'\nProcess finished with exit code: {return_code}\n')
        except Exception as exc:  # noqa: BLE001
            self.output_queue.put(f'\nError: {exc}\n')
        finally:
            self.process = None
            self.output_queue.put('__PROCESS_FINISHED__')

    def _poll_output_queue(self) -> None:
        while True:
            try:
                message = self.output_queue.get_nowait()
            except queue.Empty:
                break

            if message == '__PROCESS_FINISHED__':
                self.run_button.configure(state='normal')
                self.stop_button.configure(state='disabled')
                self.status_var.set('Ready')
            else:
                progress_match = DOWNLOAD_PROGRESS_RE.search(message)
                if progress_match:
                    self.progress['value'] = min(100.0, float(progress_match.group(1)))
                self.log(message)

        self.root.after(120, self._poll_output_queue)

    def stop_download(self) -> None:
        if self.process is not None:
            self.process.terminate()
            self.status_var.set('Stopping...')
            self.log('\nStop requested by user.\n')


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    YtDlpGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
