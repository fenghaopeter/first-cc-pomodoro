# Pomodoro Timer — User Manual

## What is the Pomodoro Technique?

The Pomodoro Technique is a time-management method: work in focused 25-minute sprints ("pomodoros"), take a short 5-minute break, then repeat. Every 4 pomodoros, take a longer 15-minute break to recharge.

---

## Quick Start

1. Run the app:
   ```
   python pomodoro.py
   ```
2. Click **Start** — the 25-minute focus timer begins.
3. Work until the timer reaches 00:00. A chime plays automatically.
4. The app switches to **Short Break** on its own — click Start to begin it.
5. Repeat.

---

## Interface Overview

```
┌─────────────────────────────┬──────────────────────────┐
│         Timer Panel         │       Right Panel        │
│                             │                          │
│  [ Work ][ Short ][ Long ]  │  Tasks                   │
│                             │  ┌──────────────────┐    │
│        ╭───────────╮        │  │ task input field │ +  │
│        │  25:00    │        │  └──────────────────┘    │
│        │  FOCUS    │        │  ○ Write report           │
│        ╰───────────╯        │  ○ Review PR              │
│                             │  ✓ Morning standup        │
│  Session 1 · 0 done today   │                          │
│  ○ ○ ○ ○                    │  ✓ Done  Delete  Clear   │
│                             │  ──────────────────────  │
│  [ Start ]  [ Reset ]       │  Today's Log             │
│                             │  10:30:45  FOCUS  25 min │
│  Settings                   │  10:55:50  SHORT  5 min  │
│  Work (min)      [ 25 ]     │                          │
│  Short break     [  5 ]     │                          │
│  Long break      [ 15 ]     │                          │
│  NOTIFY  ☑ Sound  ☑ Pop-up  │                          │
│  [ Apply ]                  │                          │
└─────────────────────────────┴──────────────────────────┘
```

---

## Timer Panel

### Mode Tabs

| Tab | Default | When it activates |
|---|---|---|
| **Work** | 25 min | Manually, or after any break completes |
| **Short Break** | 5 min | Automatically after each Focus session |
| **Long Break** | 15 min | Automatically after every 4th Focus session |

Click any tab to switch modes instantly. This also stops the current timer.

### The Ring

- The coloured arc shows how much time remains — it shrinks clockwise as time passes.
- **Red** = Focus, **Teal** = Short Break, **Purple** = Long Break.
- The dot at the arc's tip is the end-cap — it disappears when the session is complete.

### Session Info

```
Session 3  ·  2 done today
● ● ○ ○
```

- **Session N** — which focus session you are currently in.
- **N done today** — how many Focus sessions you have completed since opening the app.
- **Dots** — each dot represents one Focus session in the current cycle. They fill up as you complete sessions. After 4 dots (one full cycle), a Long Break is triggered and the dots reset.

### Controls

| Button | Action |
|---|---|
| **Start** | Begin the countdown |
| **Pause** | Freeze the timer (button becomes "Resume") |
| **Resume** | Continue from where you paused |
| **Reset** | Restart the current mode from its full duration without switching mode |

### Settings

Change the duration for any mode:

1. Click the number next to **Work**, **Short break**, or **Long break**.
2. Type a value or use the arrows (1–99 minutes).
3. Click **Apply** — the timer resets to the new duration immediately.

> Settings affect the *current* mode immediately. Other modes update the next time you switch to them.

**Notification toggles**

The **NOTIFY** row has two independent checkboxes — both are on by default:

| Checkbox | Effect when checked |
|---|---|
| **Sound** | Plays a three-tone chime on session end; a **Stop Alarm** button appears to silence it |
| **Pop-up** | Opens a small themed window showing which session just completed and a **Dismiss** button |

You can enable either, both, or neither.

---

## Task List

Use the task list to track what you plan to work on during your sessions.

### Adding a Task

- Type in the input field and press **Enter**, or click **+**.

### Managing Tasks

| Button | Action |
|---|---|
| **✓ Done** | Mark the selected task complete (or undo if already done) |
| **Delete** | Remove the selected task permanently |
| **Clear done** | Remove all completed tasks at once |

Click a task in the list to select it, then use the buttons above.

- Incomplete tasks show a **○** prefix.
- Completed tasks show a **✓** prefix and appear dimmed.

### Task Persistence

Tasks are **automatically saved** to today's log file whenever you add, complete, delete, or clear them. When you reopen the app on the same day, all tasks (including their done/undone state) are restored exactly as you left them.

---

## Daily Log

### What gets logged

Every time a session counts down to zero, one line is automatically added to both the in-app log widget and a log file on disk. **Only fully completed sessions are logged** — pausing and resetting does not create a log entry.

### In-app log widget

The "Today's Log" box at the bottom of the right panel shows all sessions completed since midnight. Entries are colour-coded:

- **Red** — Focus session
- **Teal** — Short Break
- **Purple** — Long Break

The log reloads automatically when you reopen the app on the same day, so entries persist across restarts.

### Log file on disk

Each day's entries are saved to a plain-text file in the **same folder as `pomodoro.py`**:

```
pomodoro_2026-05-25.log
```

A new file is created each calendar day. You can open it with any text editor (Notepad, VS Code, etc.).

**File format:**

```
# 2026-05-25
10:30:45  FOCUS         25 min
10:35:50  SHORT BREAK    5 min
11:01:02  FOCUS         25 min
12:27:10  LONG BREAK    15 min

# Tasks
✓  Morning standup
✓  Write report
○  Review PR
○  Update README
```

**Session entry columns:**

| Column | Example | Meaning |
|---|---|---|
| Time | `10:30:45` | When the session completed (HH:MM:SS) |
| Mode | `FOCUS` | Which type of session |
| Duration | `25 min` | How long the session was set for |

**Tasks section:**

The `# Tasks` block at the end of the file is rewritten every time you add, complete, or delete a task. Each line is prefixed with `✓` (done) or `○` (incomplete). This section is also what the app reads back when you reopen it on the same day.

### Reviewing past days

Navigate to the app folder and open any `pomodoro_YYYY-MM-DD.log` file. Each file is one day's record — you can track productivity trends, count daily pomodoros, etc.

---

## Auto-Advance Flow

The app cycles through modes automatically so you don't have to switch manually:

```
[Focus] ──done──► [Short Break] ──done──► [Focus] ──done──► [Short Break]
                                                                    │
                                          (after 4th Focus) ──done──►
                                                                    │
                                                             [Long Break]
                                                                    │
                                                             ──done──► [Focus]
```

After any break completes, the app switches back to Focus and waits for you to click Start.

---

## Notifications

When a session reaches zero, any enabled notification fires:

### Sound

A three-tone chime plays:

```
880 Hz (short) → 660 Hz (short) → 880 Hz (long)
```

The chime loops until you click **Stop Alarm**. This uses Windows' built-in audio — no extra setup needed. If no audio device is present, it is silently skipped.

### Pop-up window

A small window appears centred on the app, showing the completed session name (e.g. **FOCUS complete**) and a context hint ("Time for a break!" or "Back to work!"). Click **Dismiss** to close it.

### Enabling / disabling

Use the **Sound** and **Pop-up** checkboxes in the Settings panel. Both are on by default. You can mix and match — e.g. pop-up only when working in silence, or sound only when you need an audible alert.

---

## Tips

- **Minimise the window** while working — the countdown stays visible in the taskbar title bar (`25:00 – Pomodoro`).
- **Add your tasks before starting** so you always know what to focus on.
- **Don't skip breaks.** The short break is part of the technique — stepping away improves sustained focus.
- **Customise durations** in Settings if 25/5/15 doesn't fit your work style. Common alternatives: 50/10/30 or 45/10/20.
- **Review your log file** at the end of the day to see how many focused sessions you completed.

---

## Keyboard Shortcuts

| Key | Where | Action |
|---|---|---|
| `Enter` | Task input field | Add the typed task |

All other controls are mouse-driven.

---

## File Reference

| File | Description |
|---|---|
| `pomodoro.py` | The application — run this with Python |
| `pomodoro_YYYY-MM-DD.log` | Daily log: session entries + task list, auto-created in the same folder |
| `requirements.txt` | Dependency list (stdlib only — nothing to install) |

---

## Requirements

- Python 3.8 or later
- Windows (uses `winsound` and `tkinter`, both built into Python on Windows — no `pip install` needed)
