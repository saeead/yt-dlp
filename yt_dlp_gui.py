#!/usr/bin/env python3
"""Simple Tkinter-based GUI for yt-dlp on Windows.

This interface intentionally exposes a small, common subset of options and
allows appending custom arguments for advanced use.
"""

from __future__ import annotations

import queue
import shlex
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class YtDlpGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title('yt-dlp Simple GUI')
        self.root.geometry('920x700')
        self.root.minsize(760, 520)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()

        self.url_var = tk.StringVar()
        self.dest_var = tk.StringVar(value=str(Path.cwd()))
        self.filename_var = tk.StringVar(value='%(title)s.%(ext)s')
        self.format_var = tk.StringVar(value='bestvideo+bestaudio/best')
        self.audio_only_var = tk.BooleanVar(value=False)
        self.playlist_var = tk.BooleanVar(value=False)
        self.embed_subs_var = tk.BooleanVar(value=False)
        self.write_thumbnail_var = tk.BooleanVar(value=False)
        self.cookies_browser_var = tk.StringVar(value='')
        self.custom_args_var = tk.StringVar()

        self._build_ui()
        self.root.after(100, self._poll_output_queue)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill='both', expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(11, weight=1)

        ttk.Label(main, text='URL:').grid(row=0, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(main, textvariable=self.url_var).grid(row=0, column=1, sticky='ew', pady=(0, 6))

        ttk.Label(main, text='Destination folder:').grid(row=1, column=0, sticky='w', pady=(0, 6))
        dest_frame = ttk.Frame(main)
        dest_frame.grid(row=1, column=1, sticky='ew', pady=(0, 6))
        dest_frame.columnconfigure(0, weight=1)
        ttk.Entry(dest_frame, textvariable=self.dest_var).grid(row=0, column=0, sticky='ew')
        ttk.Button(dest_frame, text='Browse', command=self._browse_dest).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(main, text='Filename template (-o):').grid(row=2, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(main, textvariable=self.filename_var).grid(row=2, column=1, sticky='ew', pady=(0, 6))

        ttk.Label(main, text='Format (-f):').grid(row=3, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(main, textvariable=self.format_var).grid(row=3, column=1, sticky='ew', pady=(0, 6))

        options = ttk.LabelFrame(main, text='Common options', padding=10)
        options.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(8, 6))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)

        ttk.Checkbutton(options, text='Audio only (extract to mp3)', variable=self.audio_only_var).grid(
            row=0, column=0, sticky='w', padx=(0, 12), pady=2
        )
        ttk.Checkbutton(options, text='Download playlist', variable=self.playlist_var).grid(
            row=0, column=1, sticky='w', pady=2
        )
        ttk.Checkbutton(options, text='Embed subtitles', variable=self.embed_subs_var).grid(
            row=1, column=0, sticky='w', padx=(0, 12), pady=2
        )
        ttk.Checkbutton(options, text='Write thumbnail', variable=self.write_thumbnail_var).grid(
            row=1, column=1, sticky='w', pady=2
        )

        ttk.Label(main, text='Cookies from browser:').grid(row=5, column=0, sticky='w', pady=(0, 6))
        browser_combo = ttk.Combobox(
            main,
            textvariable=self.cookies_browser_var,
            state='readonly',
            values=['', 'chrome', 'firefox', 'edge', 'brave', 'opera', 'vivaldi'],
        )
        browser_combo.grid(row=5, column=1, sticky='ew', pady=(0, 6))
        browser_combo.current(0)

        ttk.Label(main, text='Custom arguments:').grid(row=6, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(main, textvariable=self.custom_args_var).grid(row=6, column=1, sticky='ew', pady=(0, 6))

        command_frame = ttk.LabelFrame(main, text='Generated command preview', padding=10)
        command_frame.grid(row=7, column=0, columnspan=2, sticky='ew', pady=(8, 6))
        command_frame.columnconfigure(0, weight=1)
        self.command_preview = tk.Text(command_frame, height=3, wrap='word')
        self.command_preview.grid(row=0, column=0, sticky='ew')
        self.command_preview.configure(state='disabled')

        buttons = ttk.Frame(main)
        buttons.grid(row=8, column=0, columnspan=2, sticky='ew', pady=(8, 6))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)

        self.run_button = ttk.Button(buttons, text='Start Download', command=self.start_download)
        self.run_button.grid(row=0, column=0, sticky='ew', padx=(0, 6))
        self.stop_button = ttk.Button(buttons, text='Stop', command=self.stop_download, state='disabled')
        self.stop_button.grid(row=0, column=1, sticky='ew', padx=6)
        ttk.Button(buttons, text='Clear Log', command=self.clear_log).grid(row=0, column=2, sticky='ew', padx=(6, 0))

        self.progress = ttk.Progressbar(main, mode='indeterminate')
        self.progress.grid(row=9, column=0, columnspan=2, sticky='ew', pady=(0, 6))

        ttk.Label(main, text='Output log:').grid(row=10, column=0, sticky='w', pady=(0, 6))
        self.log_text = tk.Text(main, wrap='word')
        self.log_text.grid(row=11, column=0, columnspan=2, sticky='nsew')

        for variable in (
            self.url_var,
            self.dest_var,
            self.filename_var,
            self.format_var,
            self.audio_only_var,
            self.playlist_var,
            self.embed_subs_var,
            self.write_thumbnail_var,
            self.cookies_browser_var,
            self.custom_args_var,
        ):
            variable.trace_add('write', lambda *_: self.update_preview())

        self.update_preview()

    def _browse_dest(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.dest_var.get() or str(Path.cwd()))
        if selected:
            self.dest_var.set(selected)

    def build_command(self) -> list[str]:
        output_template = str(Path(self.dest_var.get()) / self.filename_var.get())
        command = [sys.executable, '-m', 'yt_dlp', '--newline', '-o', output_template]

        if self.audio_only_var.get():
            command.extend(['-x', '--audio-format', 'mp3'])
        else:
            command.extend(['-f', self.format_var.get()])

        if self.playlist_var.get():
            command.append('--yes-playlist')
        else:
            command.append('--no-playlist')

        if self.embed_subs_var.get():
            command.extend(['--write-subs', '--embed-subs'])

        if self.write_thumbnail_var.get():
            command.extend(['--write-thumbnail', '--convert-thumbnails', 'jpg'])

        if self.cookies_browser_var.get():
            command.extend(['--cookies-from-browser', self.cookies_browser_var.get()])

        custom_args = self.custom_args_var.get().strip()
        if custom_args:
            command.extend(shlex.split(custom_args, posix=False))

        command.append(self.url_var.get().strip())
        return command

    def update_preview(self) -> None:
        command_text = ' '.join(self.build_command())
        self.command_preview.configure(state='normal')
        self.command_preview.delete('1.0', tk.END)
        self.command_preview.insert('1.0', command_text)
        self.command_preview.configure(state='disabled')

    def log(self, text: str) -> None:
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    def clear_log(self) -> None:
        self.log_text.delete('1.0', tk.END)

    def start_download(self) -> None:
        if self.process is not None:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning('Missing URL', 'Please provide a video/playlist URL.')
            return

        dest = Path(self.dest_var.get())
        if not dest.exists():
            messagebox.showwarning('Invalid destination', 'Destination folder does not exist.')
            return

        command = self.build_command()
        self.log(f'Running: {" ".join(command)}\n\n')

        self.run_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.progress.start(10)

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
                self.progress.stop()
            else:
                self.log(message)

        self.root.after(100, self._poll_output_queue)

    def stop_download(self) -> None:
        if self.process is not None:
            self.process.terminate()
            self.log('\nStop requested by user.\n')


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    app = YtDlpGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
