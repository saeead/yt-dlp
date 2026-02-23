#!/usr/bin/env python3
"""Modern, themeable Tkinter GUI for yt-dlp on Windows."""

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

THEMES = {
    'dark': {
        'bg': '#0A0F1C',
        'panel': '#10192D',
        'panel_alt': '#14213A',
        'panel_soft': '#1A2B48',
        'input': '#0D172C',
        'text': '#EAF1FF',
        'muted': '#9EB1D0',
        'accent': '#4EA1FF',
        'accent_soft': '#223A62',
        'ok': '#2CC98C',
        'danger': '#FF6D6D',
    },
    'light': {
        'bg': '#EEF3FB',
        'panel': '#FFFFFF',
        'panel_alt': '#F6F9FF',
        'panel_soft': '#E7EEFB',
        'input': '#FFFFFF',
        'text': '#12243F',
        'muted': '#5E7291',
        'accent': '#1D78FF',
        'accent_soft': '#DDE9FF',
        'ok': '#139F68',
        'danger': '#E14C4C',
    },
}


class YtDlpGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('Saeid YT Downloader Pro')
        self.root.geometry('1240x860')
        self.root.minsize(1040, 720)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()

        self.theme_var = tk.StringVar(value='dark')
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

        self.style = ttk.Style(self.root)
        if 'vista' in self.style.theme_names():
            self.style.theme_use('vista')

        icon_path = Path(__file__).resolve().parent / 'devscripts' / 'logo.ico'
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

        self._build_ui()
        self._load_config()
        self._apply_theme()

        for variable in (
            self.theme_var,
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

        self.root.after(120, self._poll_output_queue)
        self.update_preview()

    def _build_ui(self) -> None:
        self.main = ttk.Frame(self.root, style='App.TFrame', padding=14)
        self.main.pack(fill='both', expand=True)
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        self._build_header()

        content = ttk.Frame(self.main, style='App.TFrame')
        content.grid(row=1, column=0, sticky='nsew')
        content.columnconfigure(0, weight=13)
        content.columnconfigure(1, weight=9)
        content.rowconfigure(0, weight=1)

        self.left = ttk.Frame(content, style='App.TFrame')
        self.left.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self.left.columnconfigure(0, weight=1)
        self.left.rowconfigure(5, weight=1)

        self.right = ttk.Frame(content, style='App.TFrame')
        self.right.grid(row=0, column=1, sticky='nsew')
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(2, weight=1)

        self._build_source_card()
        self._build_destination_card()
        self._build_quality_card()
        self._build_advanced_card()
        self._build_preview_card()

        self._build_actions_card()
        self._build_progress_card()
        self._build_log_card()

    def _build_header(self) -> None:
        bar = ttk.Frame(self.main, style='Glass.TFrame', padding=(18, 14))
        bar.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        bar.columnconfigure(1, weight=1)

        ttk.Label(bar, text='Saeid YT Downloader Pro', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(
            bar,
            text='Design-system inspired layout • fast workflows • pro controls',
            style='Subtitle.TLabel',
        ).grid(row=1, column=0, sticky='w', pady=(2, 0))

        right = ttk.Frame(bar, style='Glass.TFrame')
        right.grid(row=0, column=2, rowspan=2, sticky='e')
        ttk.Label(right, text='Theme', style='Tiny.TLabel').grid(row=0, column=0, padx=(0, 8))
        ttk.Combobox(
            right,
            textvariable=self.theme_var,
            state='readonly',
            values=['dark', 'light'],
            width=10,
            style='Selected.TCombobox',
        ).grid(row=0, column=1)

    def _build_source_card(self) -> None:
        card = ttk.LabelFrame(self.left, text='Source & Presets', style='Card.TLabelframe', padding=14)
        card.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text='Preset', style='Field.TLabel').grid(row=0, column=0, sticky='w')
        preset_row = ttk.Frame(card, style='CardInner.TFrame')
        preset_row.grid(row=0, column=1, sticky='ew', pady=(0, 6))
        preset_row.columnconfigure(0, weight=1)
        self.preset_combo = ttk.Combobox(
            preset_row,
            textvariable=self.preset_var,
            state='readonly',
            values=['custom', 'best-video', 'audio-mp3', 'subtitles-only', 'thumbnail-only'],
            style='Selected.TCombobox',
        )
        self.preset_combo.grid(row=0, column=0, sticky='ew')
        self.preset_combo.bind('<<ComboboxSelected>>', self._apply_preset)
        ttk.Button(preset_row, text='Save defaults', style='Subtle.TButton', command=self._save_config).grid(
            row=0, column=1, padx=(8, 0)
        )

        hdr = ttk.Frame(card, style='CardInner.TFrame')
        hdr.grid(row=1, column=0, sticky='w')
        ttk.Label(hdr, text='URLs', style='Field.TLabel').pack(side='left')
        ttk.Button(hdr, text='Paste', style='Subtle.TButton', command=self._paste_urls).pack(side='left', padx=(8, 0))

        self.urls_text = tk.Text(card, height=5, wrap='word', relief='flat', padx=10, pady=10)
        self.urls_text.grid(row=1, column=1, sticky='ew')
        self.urls_text.bind('<KeyRelease>', lambda *_: self.update_preview())
        self.urls_text.bind('<Button-3>', self._show_urls_context_menu)

    def _build_destination_card(self) -> None:
        card = ttk.LabelFrame(self.left, text='Destination', style='Card.TLabelframe', padding=14)
        card.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text='Folder', style='Field.TLabel').grid(row=0, column=0, sticky='w')
        folder_row = ttk.Frame(card, style='CardInner.TFrame')
        folder_row.grid(row=0, column=1, sticky='ew', pady=(0, 6))
        folder_row.columnconfigure(0, weight=1)
        ttk.Entry(folder_row, textvariable=self.dest_var).grid(row=0, column=0, sticky='ew')
        ttk.Button(folder_row, text='Browse', style='Subtle.TButton', command=self._browse_dest).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(card, text='Filename template', style='Field.TLabel').grid(row=1, column=0, sticky='w')
        ttk.Entry(card, textvariable=self.filename_var).grid(row=1, column=1, sticky='ew')

    def _build_quality_card(self) -> None:
        card = ttk.LabelFrame(self.left, text='Quality & Media', style='Card.TLabelframe', padding=14)
        card.grid(row=2, column=0, sticky='ew', pady=(0, 8))
        card.columnconfigure(1, weight=1)
        card.columnconfigure(3, weight=1)

        ttk.Label(card, text='Download mode', style='Field.TLabel').grid(row=0, column=0, sticky='w', pady=3)
        ttk.Combobox(
            card,
            textvariable=self.media_mode_var,
            state='readonly',
            values=['video+audio', 'video-only', 'audio-only'],
            style='Selected.TCombobox',
        ).grid(row=0, column=1, sticky='ew', padx=(8, 12), pady=3)

        ttk.Label(card, text='Video quality', style='Field.TLabel').grid(row=0, column=2, sticky='w', pady=3)
        ttk.Combobox(
            card,
            textvariable=self.video_quality_var,
            state='readonly',
            values=list(VIDEO_HEIGHT_MAP.keys()),
            style='Selected.TCombobox',
        ).grid(row=0, column=3, sticky='ew', padx=(8, 0), pady=3)

        ttk.Label(card, text='Audio quality', style='Field.TLabel').grid(row=1, column=0, sticky='w', pady=3)
        ttk.Combobox(
            card,
            textvariable=self.audio_quality_var,
            state='readonly',
            values=list(AUDIO_ABR_MAP.keys()),
            style='Selected.TCombobox',
        ).grid(row=1, column=1, sticky='ew', padx=(8, 12), pady=3)

        ttk.Label(card, text='Audio format', style='Field.TLabel').grid(row=1, column=2, sticky='w', pady=3)
        ttk.Combobox(
            card,
            textvariable=self.audio_format_var,
            state='readonly',
            values=['mp3', 'm4a', 'aac', 'opus', 'vorbis', 'wav'],
            style='Selected.TCombobox',
        ).grid(row=1, column=3, sticky='ew', padx=(8, 0), pady=3)

        ttk.Checkbutton(card, text='Manual format override (-f)', variable=self.manual_format_var, style='Switch.TCheckbutton').grid(
            row=2, column=0, sticky='w', pady=(8, 2)
        )
        ttk.Entry(card, textvariable=self.format_var).grid(row=2, column=1, columnspan=3, sticky='ew', pady=(8, 2))

    def _build_advanced_card(self) -> None:
        card = ttk.LabelFrame(self.left, text='Advanced Options', style='Card.TLabelframe', padding=14)
        card.grid(row=3, column=0, sticky='ew', pady=(0, 8))
        card.columnconfigure(1, weight=1)

        checks = ttk.Frame(card, style='CardInner.TFrame')
        checks.grid(row=0, column=0, columnspan=2, sticky='ew')
        ttk.Checkbutton(checks, text='Playlist', variable=self.playlist_var, style='Switch.TCheckbutton').pack(side='left', padx=(0, 12))
        ttk.Checkbutton(checks, text='Embed subtitles', variable=self.embed_subs_var, style='Switch.TCheckbutton').pack(side='left', padx=(0, 12))
        ttk.Checkbutton(checks, text='Write thumbnail', variable=self.write_thumbnail_var, style='Switch.TCheckbutton').pack(side='left')

        ttk.Label(card, text='Cookies browser', style='Field.TLabel').grid(row=1, column=0, sticky='w', pady=4)
        ttk.Combobox(
            card,
            textvariable=self.cookies_browser_var,
            state='readonly',
            values=['', 'chrome', 'firefox', 'edge', 'brave', 'opera', 'vivaldi'],
            style='Selected.TCombobox',
        ).grid(row=1, column=1, sticky='ew', pady=4)

        ttk.Label(card, text='Custom arguments', style='Field.TLabel').grid(row=2, column=0, sticky='w', pady=4)
        ttk.Entry(card, textvariable=self.custom_args_var).grid(row=2, column=1, sticky='ew', pady=4)

    def _build_preview_card(self) -> None:
        card = ttk.LabelFrame(self.left, text='Command Preview', style='Card.TLabelframe', padding=14)
        card.grid(row=4, column=0, sticky='nsew')
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)
        self.command_preview = tk.Text(card, height=5, wrap='word', relief='flat', padx=10, pady=10)
        self.command_preview.grid(row=0, column=0, sticky='nsew')
        self.command_preview.configure(state='disabled')

    def _build_actions_card(self) -> None:
        card = ttk.LabelFrame(self.right, text='Actions', style='Card.TLabelframe', padding=14)
        card.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        for i in range(3):
            card.columnconfigure(i, weight=1)

        self.run_button = ttk.Button(card, text='Start Download', style='Accent.TButton', command=self.start_download)
        self.run_button.grid(row=0, column=0, sticky='ew', padx=(0, 6))
        self.stop_button = ttk.Button(card, text='Stop', style='Danger.TButton', state='disabled', command=self.stop_download)
        self.stop_button.grid(row=0, column=1, sticky='ew', padx=6)
        ttk.Button(card, text='Clear Log', style='Subtle.TButton', command=self.clear_log).grid(row=0, column=2, sticky='ew', padx=(6, 0))
        ttk.Button(card, text='Reset', style='Subtle.TButton', command=self._reset_fields).grid(row=1, column=0, columnspan=3, sticky='ew', pady=(8, 0))

    def _build_progress_card(self) -> None:
        card = ttk.LabelFrame(self.right, text='Progress', style='Card.TLabelframe', padding=14)
        card.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        card.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(card, mode='determinate', maximum=100, style='Modern.Horizontal.TProgressbar')
        self.progress.grid(row=0, column=0, sticky='ew')
        ttk.Label(card, textvariable=self.status_var, style='Tiny.TLabel').grid(row=1, column=0, sticky='w', pady=(8, 0))

    def _build_log_card(self) -> None:
        card = ttk.LabelFrame(self.right, text='Live Log', style='Card.TLabelframe', padding=14)
        card.grid(row=2, column=0, sticky='nsew')
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.log_text = tk.Text(card, wrap='word', relief='flat', padx=10, pady=10)
        self.log_text.grid(row=0, column=0, sticky='nsew')

    def _apply_theme(self) -> None:
        p = THEMES[self.theme_var.get()]
        selected_bg = '#FFFFFF'
        selected_fg = '#0F172A'

        self.root.configure(bg=p['bg'])
        self.style.configure('App.TFrame', background=p['bg'])
        self.style.configure('Glass.TFrame', background=p['panel'])
        self.style.configure('CardInner.TFrame', background=p['panel'])

        self.style.configure('Title.TLabel', background=p['panel'], foreground=p['text'], font=('Segoe UI Semibold', 20))
        self.style.configure('Subtitle.TLabel', background=p['panel'], foreground=p['muted'], font=('Segoe UI', 10))
        self.style.configure('Tiny.TLabel', background=p['panel'], foreground=p['muted'], font=('Segoe UI', 9))
        self.style.configure('Field.TLabel', background=p['panel'], foreground=p['muted'], font=('Segoe UI', 10))

        self.style.configure('Card.TLabelframe', background=p['panel'], foreground=p['text'])
        self.style.configure('Card.TLabelframe.Label', background=p['panel'], foreground=p['text'], font=('Segoe UI Semibold', 10))

        self.style.configure('TEntry', fieldbackground=p['input'], foreground=p['text'], insertcolor=p['text'])
        self.style.configure('TCombobox', fieldbackground=p['input'], background=p['panel_alt'], foreground=p['text'])
        self.style.configure(
            'Selected.TCombobox',
            fieldbackground=selected_bg,
            background=selected_bg,
            foreground=selected_fg,
            arrowcolor=selected_fg,
        )
        self.style.map(
            'Selected.TCombobox',
            fieldbackground=[('readonly', selected_bg)],
            foreground=[('readonly', selected_fg)],
            selectbackground=[('readonly', selected_bg)],
            selectforeground=[('readonly', selected_fg)],
        )
        self.root.option_add('*TCombobox*Listbox.background', selected_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', selected_fg)
        self.root.option_add('*TCombobox*Listbox.selectBackground', p['accent'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')
        self.root.option_add('*TCombobox*Listbox.font', 'Segoe UI 10')

        self.style.configure('Accent.TButton', font=('Segoe UI Semibold', 10), background=p['accent'], foreground='white', borderwidth=0)
        self.style.map(
            'Accent.TButton',
            background=[('disabled', p['panel_soft']), ('active', p['accent'])],
            foreground=[('disabled', p['muted']), ('active', '#FFFFFF')],
        )
        self.style.configure('Danger.TButton', font=('Segoe UI Semibold', 10), background=p['danger'], foreground='white', borderwidth=0)
        self.style.map(
            'Danger.TButton',
            background=[('disabled', p['panel_soft']), ('active', p['danger'])],
            foreground=[('disabled', p['muted']), ('active', '#FFFFFF')],
        )
        self.style.configure('Subtle.TButton', font=('Segoe UI', 10), background=p['accent_soft'], foreground=p['text'])
        self.style.map(
            'Subtle.TButton',
            background=[('disabled', p['panel_soft']), ('active', p['accent_soft'])],
            foreground=[('disabled', p['muted']), ('active', p['text'])],
        )
        self.style.configure('Switch.TCheckbutton', background=p['panel'], foreground=p['text'])

        self.style.configure(
            'Modern.Horizontal.TProgressbar',
            troughcolor=p['panel_soft'],
            background=p['ok'],
            lightcolor=p['ok'],
            darkcolor=p['ok'],
        )

        for widget in (self.urls_text, self.command_preview, self.log_text):
            widget.configure(bg=p['input'], fg=p['text'], insertbackground=p['text'])

    def _get_urls(self) -> list[str]:
        return [line.strip() for line in self.urls_text.get('1.0', tk.END).splitlines() if line.strip()]

    def _paste_urls(self) -> None:
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return
        if text:
            self.urls_text.insert(tk.INSERT, text)
            self.update_preview()

    def _show_urls_context_menu(self, event: tk.Event[tk.Misc]) -> None:
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label='Paste', command=self._paste_urls)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

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
            'theme': self.theme_var.get(),
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

        self.theme_var.set(data.get('theme', self.theme_var.get()))
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

        video_part = 'bestvideo' if video_choice is None else ('worstvideo' if video_choice == 'worst' else f'bestvideo[height<={video_choice}]')
        audio_part = 'bestaudio' if audio_choice is None else ('worstaudio' if audio_choice == 'worst' else f'bestaudio[abr<={audio_choice}]')
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
        self._apply_theme()
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
    YtDlpGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
