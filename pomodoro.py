import tkinter as tk
import winsound
import threading
import time
import datetime
import pathlib
import math

# ─────────────────────────────────────────────────────────────────────────────
#  Design tokens
# ─────────────────────────────────────────────────────────────────────────────
C = {
    'bg':      '#0b0b13',   # window background
    'surface': '#111119',   # panel fill
    'card':    '#171722',   # unused — kept for symmetry
    'card2':   '#1a1a26',   # settings / log card
    'border':  '#252538',   # 1-px separator line
    'work':    '#f0607e',   # focus red-pink
    'short':   '#3dcfb0',   # short-break teal
    'long':    '#9b7ff4',   # long-break purple
    'text':    '#edeef8',   # primary text
    'sub':     '#52526a',   # secondary text
    'dim':     '#1e1e2c',   # inactive fill / seg track
    'done':    '#272738',   # done-task text colour
    'ring_bg': '#181828',   # timer ring track
}

MODE_COLOR = {'work': C['work'], 'short_break': C['short'], 'long_break': C['long']}
MODE_LABEL = {'work': 'FOCUS', 'short_break': 'SHORT BREAK', 'long_break': 'LONG BREAK'}
MODE_MIN   = {'work': 25, 'short_break': 5, 'long_break': 15}
CYCLE      = 4
LOG_DIR    = pathlib.Path(__file__).parent


# ─────────────────────────────────────────────────────────────────────────────
#  Colour utilities
# ─────────────────────────────────────────────────────────────────────────────
def _adj(h, n):
    """Lighten (n>0) or darken (n<0) a hex colour."""
    h = h.lstrip('#')
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    return '#{:02x}{:02x}{:02x}'.format(*[max(0, min(255, x + n)) for x in (r, g, b)])


def _rrect(cv, x1, y1, x2, y2, r=12, **kw):
    """Draw a smooth rounded-rectangle polygon on canvas cv."""
    return cv.create_polygon(
        x1+r, y1,    x2-r, y1,
        x2,   y1,    x2,   y1+r,
        x2,   y2-r,  x2,   y2,
        x2-r, y2,    x1+r, y2,
        x1,   y2,    x1,   y2-r,
        x1,   y1+r,  x1,   y1,
        smooth=True, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  Custom widgets
# ─────────────────────────────────────────────────────────────────────────────
class PillBtn(tk.Canvas):
    """A Canvas that renders as a rounded pill button."""

    def __init__(self, parent, text, color, fg='white', command=None,
                 font=('Segoe UI', 12, 'bold'), w=150, h=46, r=23):
        super().__init__(parent, width=w, height=h,
                         bg=parent.cget('bg'), highlightthickness=0, cursor='hand2')
        self._t, self._fg, self._font = text, fg, font
        self._color = color
        self._hover = _adj(color, 24)
        self._cmd   = command
        self._bw, self._bh, self._br = w, h, r  # _w/_h are reserved by tkinter internals
        self._paint(color)
        self.bind('<Enter>',    lambda _: self._paint(self._hover))
        self.bind('<Leave>',    lambda _: self._paint(self._color))
        self.bind('<Button-1>', lambda _: self._cmd() if self._cmd else None)

    def _paint(self, bg):
        self.delete('all')
        _rrect(self, 0, 0, self._bw, self._bh, self._br, fill=bg, outline='')
        self.create_text(self._bw // 2, self._bh // 2,
                         text=self._t, fill=self._fg, font=self._font)

    def set_text(self, t):
        self._t = t
        self._paint(self._color)

    def set_color(self, color):
        self._color = color
        self._hover = _adj(color, 24)
        self._paint(color)


class SmallBtn(tk.Button):
    """Flat text button with enter/leave hover."""

    def __init__(self, parent, text, bg, fg, command, font=('Segoe UI', 9, 'bold')):
        super().__init__(parent, text=text, bg=bg, fg=fg, relief='flat',
                         font=font, padx=12, pady=6, bd=0,
                         cursor='hand2', command=command,
                         activebackground=_adj(bg, 12), activeforeground=fg)
        hover = _adj(bg, 12)
        self.bind('<Enter>', lambda _: self.config(bg=hover))
        self.bind('<Leave>', lambda _: self.config(bg=bg))


# ─────────────────────────────────────────────────────────────────────────────
#  Application
# ─────────────────────────────────────────────────────────────────────────────
class PomodoroApp:

    def __init__(self, root):
        self.root = root
        self.root.title('Pomodoro')
        self.root.resizable(False, False)
        self.root.configure(bg=C['bg'])

        self.minutes    = {k: tk.IntVar(value=v) for k, v in MODE_MIN.items()}
        self.mode       = 'work'
        self.running    = False
        self.time_left  = MODE_MIN['work'] * 60
        self.total_time = self.time_left
        self.sessions   = 0
        self.tasks      = []
        self._thread    = None
        self._beeping   = False   # True while the end-of-session alarm is looping

        self._build()
        self._select_mode('work')
        self._load_log()

    # ── Top-level layout ─────────────────────────────────────────────────────

    def _build(self):
        outer = tk.Frame(self.root, bg=C['bg'])
        outer.pack(padx=26, pady=26)

        left = tk.Frame(outer, bg=C['bg'])
        left.grid(row=0, column=0, padx=(0, 22), sticky='n')

        right = tk.Frame(outer, bg=C['bg'])
        right.grid(row=0, column=1, sticky='nsew')

        self._build_timer(left)
        self._build_right(right)

    # ── Timer column ─────────────────────────────────────────────────────────

    def _build_timer(self, parent):
        # Segmented control pill
        pill = tk.Frame(parent, bg=C['dim'], padx=4, pady=4)
        pill.pack()
        self._seg_btns = {}
        for key, lbl in [('work', 'Work'), ('short_break', 'Short Break'), ('long_break', 'Long Break')]:
            b = tk.Button(pill, text=lbl, relief='flat', bg=C['dim'], fg=C['sub'],
                          font=('Segoe UI', 9), padx=16, pady=7,
                          bd=0, highlightthickness=0, cursor='hand2',
                          activebackground=_adj(C['dim'], 14), activeforeground=C['text'],
                          command=lambda k=key: self._select_mode(k))
            b.pack(side='left', padx=1)
            self._seg_btns[key] = b

        # Ring canvas
        self._cs = 312
        self._cv  = tk.Canvas(parent, width=self._cs, height=self._cs,
                              bg=C['bg'], highlightthickness=0)
        self._cv.pack(pady=(14, 0))

        # Session label + dots
        self._sess_lbl = tk.Label(parent, bg=C['bg'], fg=C['sub'],
                                  font=('Segoe UI', 10))
        self._sess_lbl.pack(pady=(4, 2))

        self._dots_f = tk.Frame(parent, bg=C['bg'])
        self._dots_f.pack(pady=(0, 16))

        # Control buttons
        ctrl = tk.Frame(parent, bg=C['bg'])
        ctrl.pack()
        self._start_btn = PillBtn(ctrl, 'Start', C['work'],
                                  command=self._toggle, w=152, h=48)
        self._start_btn.pack(side='left', padx=(0, 10))
        PillBtn(ctrl, 'Reset', C['dim'], fg=C['text'],
                command=self._reset, w=104, h=48).pack(side='left')

        # Settings card
        self._build_settings(parent)

    def _build_settings(self, parent):
        card = tk.Frame(parent, bg=C['card2'], padx=18, pady=14)
        card.pack(pady=(20, 0), fill='x')

        tk.Label(card, text='SETTINGS', bg=C['card2'], fg=C['sub'],
                 font=('Segoe UI', 8, 'bold')).grid(
                     row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))

        for col, (key, label) in enumerate([('work', 'Work'), ('short_break', 'Short'), ('long_break', 'Long')]):
            tk.Label(card, text=label, bg=C['card2'], fg=C['sub'],
                     font=('Segoe UI', 8)).grid(row=1, column=col, padx=(0, 16), sticky='w')
            sp = tk.Spinbox(card, from_=1, to=99, textvariable=self.minutes[key],
                            width=4, bg=C['bg'], fg=C['text'], relief='flat',
                            buttonbackground=C['dim'], insertbackground=C['text'],
                            font=('Segoe UI', 12, 'bold'))
            sp.grid(row=2, column=col, padx=(0, 16), pady=(4, 0), sticky='w')

        PillBtn(card, 'Apply', C['work'], command=self._apply_settings,
                font=('Segoe UI', 9, 'bold'), w=108, h=34, r=17
                ).grid(row=3, column=0, columnspan=3, pady=(14, 0))

    # ── Ring drawing ─────────────────────────────────────────────────────────

    def _draw(self):
        cv = self._cv
        cv.delete('all')
        cx = cy = self._cs // 2
        r, sw = 122, 18
        color = MODE_COLOR[self.mode]

        # Glow halos (stippled ovals give a soft outer bloom)
        for gr, stip in [(r + sw//2 + 10, 'gray12'), (r + sw//2 + 5, 'gray25')]:
            cv.create_oval(cx-gr, cy-gr, cx+gr, cy+gr,
                           outline=color, width=1, stipple=stip)

        # Ring track
        cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                       outline=C['ring_bg'], width=sw)

        # Progress arc + end-cap
        frac = self.time_left / self.total_time if self.total_time else 0
        if frac > 0:
            cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                          start=90, extent=-360 * frac,
                          outline=color, width=sw, style='arc')
            angle   = math.radians(90 - 360 * frac)
            ex, ey  = cx + r * math.cos(angle), cy - r * math.sin(angle)
            cr      = sw // 2 + 2
            cv.create_oval(ex-cr, ey-cr, ex+cr, ey+cr, fill=color, outline='')

        # Start-cap (12 o'clock dot)
        cr = sw // 2 + 1
        cv.create_oval(cx-cr, cy-r-cr, cx+cr, cy-r+cr,
                       fill=color if frac > 0.98 else C['ring_bg'], outline='')

        # Countdown text  (large)
        mm, ss = divmod(self.time_left, 60)
        cv.create_text(cx, cy - 14, text=f'{mm:02d}:{ss:02d}',
                       fill=C['text'], font=('Segoe UI', 54, 'bold'))
        cv.create_text(cx, cy + 40, text=MODE_LABEL[self.mode],
                       fill=color, font=('Segoe UI', 10, 'bold'))

        # Window title bar mirrors the countdown
        self.root.title(f'{mm:02d}:{ss:02d} – Pomodoro')

        # Progress dots
        for w in self._dots_f.winfo_children():
            w.destroy()
        pos = self.sessions % CYCLE
        for i in range(CYCLE):
            filled = i < pos
            tk.Label(self._dots_f,
                     text='●' if filled else '○',
                     bg=C['bg'],
                     fg=color if filled else C['dim'],
                     font=('Segoe UI', 12)).pack(side='left', padx=3)

        self._sess_lbl.config(
            text=f'Session {self.sessions + 1}   ·   {self.sessions} done today')

    # ── Mode / timer logic ────────────────────────────────────────────────────

    def _select_mode(self, mode, *, auto=False):
        if not auto:
            self._beeping = False   # manual tab switch dismisses alarm
        self.running    = False
        self.mode       = mode
        secs            = self.minutes[mode].get() * 60
        self.time_left  = secs
        self.total_time = secs
        color = MODE_COLOR[mode]

        self._start_btn.set_color(color)
        self._start_btn.set_text('Start')

        for k, btn in self._seg_btns.items():
            if k == mode:
                btn.config(bg=_adj(C['dim'], 16), fg=color,
                           font=('Segoe UI', 9, 'bold'))
            else:
                btn.config(bg=C['dim'], fg=C['sub'],
                           font=('Segoe UI', 9))

        self._draw()

    def _toggle(self):
        if self._beeping:               # alarm is ringing — this click is "Stop Alarm"
            self._beeping = False
            self._start_btn.set_text('Start')
            return
        if self.running:
            self.running = False
            self._start_btn.set_text('Resume')
        else:
            self.running = True
            self._start_btn.set_text('Pause')
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._tick, daemon=True)
                self._thread.start()

    def _tick(self):
        while self.running and self.time_left > 0:
            time.sleep(1)
            if self.running:
                self.time_left -= 1
                self.root.after(0, self._draw)
        if self.time_left == 0:
            self.root.after(0, self._done)

    def _done(self):
        self.running  = False
        self._beeping = True
        threading.Thread(target=self._beep, daemon=True).start()
        self._log_session(self.mode, self.total_time // 60)
        if self.mode == 'work':
            self.sessions += 1
            next_mode = 'long_break' if self.sessions % CYCLE == 0 else 'short_break'
        else:
            next_mode = 'work'
        self._select_mode(next_mode, auto=True)
        # Override the "Start" label that _select_mode just set
        self._start_btn.set_text('Stop Alarm')

    def _beep(self):
        # Loops the three-tone chime until _beeping is cleared by user action.
        # Checks the flag between each tone so it stops promptly when dismissed.
        while self._beeping:
            for freq, dur in [(880, 250), (660, 250), (880, 400)]:
                if not self._beeping:
                    return
                try:
                    winsound.Beep(freq, dur)
                except Exception:
                    pass
                time.sleep(0.05)
            # Pause between repetitions; check flag so we don't sleep a full
            # second after the user already pressed Stop Alarm
            for _ in range(10):
                if not self._beeping:
                    return
                time.sleep(0.1)

    def _reset(self):
        self._beeping  = False
        self.running   = False
        self.time_left = self.total_time
        self._start_btn.set_text('Start')
        self._draw()

    def _apply_settings(self):
        secs            = self.minutes[self.mode].get() * 60
        self.time_left  = secs
        self.total_time = secs
        self.running    = False
        self._start_btn.set_text('Start')
        self._draw()

    # ── Right column ─────────────────────────────────────────────────────────

    def _build_right(self, parent):
        self._build_tasks(parent)
        tk.Frame(parent, bg=C['border'], height=1).pack(fill='x', pady=16)
        self._build_log(parent)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def _build_tasks(self, parent):
        tk.Label(parent, text='Tasks', bg=C['bg'], fg=C['text'],
                 font=('Segoe UI', 13, 'bold')).pack(anchor='w')

        # Entry + add button
        row = tk.Frame(parent, bg=C['bg'])
        row.pack(fill='x', pady=(10, 8))

        self._entry = tk.Entry(row, bg=C['card2'], fg=C['text'], relief='flat',
                               font=('Segoe UI', 11), insertbackground=C['text'],
                               highlightthickness=1, highlightcolor=C['work'],
                               highlightbackground=C['border'])
        self._entry.pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 8))
        self._entry.bind('<Return>', lambda _: self._add_task())

        PillBtn(row, '+', C['work'], command=self._add_task,
                font=('Segoe UI', 16, 'bold'), w=44, h=40, r=20).pack(side='left')

        # Listbox
        lf = tk.Frame(parent, bg=C['card2'])
        lf.pack(fill='both', expand=True)

        sb = tk.Scrollbar(lf, bg=C['dim'], troughcolor=C['card2'],
                          relief='flat', width=5)
        sb.pack(side='right', fill='y')

        self._lb = tk.Listbox(lf, bg=C['card2'], fg=C['text'], relief='flat',
                              font=('Segoe UI', 11), selectbackground=C['border'],
                              selectforeground=C['text'], activestyle='none',
                              yscrollcommand=sb.set, height=8, width=28,
                              bd=0, highlightthickness=0)
        self._lb.pack(fill='both', expand=True, padx=6, pady=6)
        sb.config(command=self._lb.yview)

        # Action row
        acts = tk.Frame(parent, bg=C['bg'])
        acts.pack(fill='x', pady=(8, 0))

        SmallBtn(acts, '✓ Done',    '#152b22', C['short'], self._toggle_done).pack(side='left', padx=(0, 6))
        SmallBtn(acts, 'Delete',    '#2b1520', C['work'],  self._delete_task).pack(side='left')

        clear = tk.Button(acts, text='Clear done', bg=C['bg'], fg=C['sub'],
                          relief='flat', font=('Segoe UI', 9), padx=10, pady=6,
                          bd=0, cursor='hand2', command=self._clear_done,
                          activebackground=C['bg'], activeforeground=C['text'])
        clear.pack(side='right')
        clear.bind('<Enter>', lambda _: clear.config(fg=C['text']))
        clear.bind('<Leave>', lambda _: clear.config(fg=C['sub']))

    def _refresh_lb(self):
        self._lb.delete(0, 'end')
        for task in self.tasks:
            self._lb.insert('end', ('✓  ' if task['done'] else '○  ') + task['text'])
            if task['done']:
                self._lb.itemconfig('end', fg=C['done'])

    def _add_task(self):
        text = self._entry.get().strip()
        if text:
            self.tasks.append({'text': text, 'done': False})
            self._refresh_lb()
            self._entry.delete(0, 'end')

    def _toggle_done(self):
        sel = self._lb.curselection()
        if sel:
            idx = sel[0]
            self.tasks[idx]['done'] = not self.tasks[idx]['done']
            self._refresh_lb()
            self._lb.selection_set(idx)

    def _delete_task(self):
        sel = self._lb.curselection()
        if sel:
            del self.tasks[sel[0]]
            self._refresh_lb()

    def _clear_done(self):
        self.tasks = [t for t in self.tasks if not t['done']]
        self._refresh_lb()

    # ── Daily log ─────────────────────────────────────────────────────────────

    def _log_path(self):
        return LOG_DIR / f'pomodoro_{datetime.date.today()}.log'

    def _log_session(self, mode, duration_min):
        ts    = datetime.datetime.now().strftime('%H:%M:%S')
        label = MODE_LABEL[mode].ljust(12)
        line  = f'{ts}  {label}  {duration_min} min'
        try:
            with open(self._log_path(), 'a', encoding='utf-8') as f:
                if f.tell() == 0:
                    f.write(f'# {datetime.date.today()}\n')
                f.write(line + '\n')
        except OSError:
            pass
        self._append_log(line, mode)

    def _load_log(self):
        p = self._log_path()
        if not p.exists():
            return
        inv = {v: k for k, v in MODE_LABEL.items()}
        try:
            for raw in p.read_text(encoding='utf-8').splitlines():
                if raw.startswith('#'):
                    continue
                mode = next((m for lbl, m in inv.items() if lbl in raw), None)
                self._append_log(raw, mode)
        except OSError:
            pass

    def _append_log(self, line, mode=None):
        self._log_text.config(state='normal')
        self._log_text.insert('end', line + '\n', mode or 'default')
        self._log_text.see('end')
        self._log_text.config(state='disabled')

    def _build_log(self, parent):
        hdr = tk.Frame(parent, bg=C['bg'])
        hdr.pack(fill='x', pady=(0, 8))
        tk.Label(hdr, text="Today's Log", bg=C['bg'], fg=C['text'],
                 font=('Segoe UI', 11, 'bold')).pack(side='left')
        tk.Label(hdr, text=self._log_path().name, bg=C['bg'], fg=C['sub'],
                 font=('Consolas', 7)).pack(side='right', pady=(5, 0))

        lf = tk.Frame(parent, bg=C['card2'])
        lf.pack(fill='both', expand=True)
        sb = tk.Scrollbar(lf, bg=C['dim'], troughcolor=C['card2'],
                          relief='flat', width=5)
        sb.pack(side='right', fill='y')

        self._log_text = tk.Text(lf, bg=C['card2'], fg=C['sub'],
                                 relief='flat', font=('Consolas', 9),
                                 height=5, width=30, wrap='none',
                                 yscrollcommand=sb.set, state='disabled',
                                 cursor='arrow', bd=0, highlightthickness=0,
                                 padx=10, pady=8,
                                 selectbackground=C['border'])
        self._log_text.pack(fill='both', expand=True)
        sb.config(command=self._log_text.yview)

        for mode, color in MODE_COLOR.items():
            self._log_text.tag_config(mode, foreground=color)
        self._log_text.tag_config('default', foreground=C['sub'])


if __name__ == '__main__':
    root = tk.Tk()
    PomodoroApp(root)
    root.mainloop()
