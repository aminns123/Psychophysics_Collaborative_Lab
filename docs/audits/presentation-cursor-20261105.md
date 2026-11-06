# Presentation cursor ownership — 5 November 2026

The shared Presentation backend used by official Test and Run paths did not
explicitly hide the OS pointer. Pyglet 1.5.27's Windows focus handler can also
request platform visibility when restoring non-exclusive input, overriding a
previous logical hidden choice. Its remembered keyboard focus and mouse-enter
flags are not sufficient for a stationary pointer at window entry.

The existing output-window factory now receives a small Pyglet Window subclass.
It selects hidden cursor visibility before showing the presentation window,
checks the actual foreground HWND and that window's client coordinates, and
reconciles native activation/cursor messages with the requested visibility.
It does not move or clip the pointer. The TUI and other applications retain
their cursor; close restores visibility before releasing the window. Constructor
errors close the acquired window, and existing RunContext cleanup handles abort,
completion and error. No timer, per-frame cursor poll, frame-count, flip,
response-collection or stimulus-rendering code was changed.

All ten official response paradigms are keyboard-based. Mouse-driven custom
windows are untouched. Authors using the shared backend can explicitly use
`Presentation(..., show_mouse_cursor=True)` or the existing
`presentation.window.set_mouse_visible(True)`; subsequent focus/cursor events
honour that choice. No new dependency, experiment parameter registry or global
Windows cursor-counter manipulation is introduced. The implementation delegates
the actual visibility change to the existing Pyglet backend.

Windows cursor visibility is a counted OS state, so repeated global hide/show
loops are unsuitable here ([Microsoft ShowCursor documentation](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showcursor)).
Normal Pyglet visibility is window-scoped ([Pyglet mouse guide](https://pyglet.readthedocs.io/en/latest/programming_guide/mouse.html#changing-the-mouse-cursor));
the pinned 1.5.27 Windows implementation was also inspected directly.

## Native verification

Opt-in command: `python scripts/verify_cursor_windows.py`. It briefly creates
blank windows and moves the pointer. A supervisor bounds the probe at 45 seconds
and restores the original pointer position/focus; child controls exit if their
owner exits. It uses no participant, calibration or installation records.

Verified on **Windows 11 Home, build 26300**, with two detected monitors at
origins **(0, 0)** and **(-1920, 148)**. All 13 native scenarios passed:

- Windowed and fullscreen normal/Escape/error cleanup on each monitor.
- Initial stationary-pointer hiding, motion, transfer to another application's
  real native window, focus return and explicit visible-cursor opt-in in every case.
- OS cursor recovery after forced termination of an isolated hidden-cursor
  process, without relying on Python finally/close callbacks.

The probe models the existing manual-dispatch Escape contract: Escape requests
exit; the owning runtime then closes the window. Mocked tests also cover initial
resolution/show failures, stale focus state and negative monitor origins. This
checks cursor ownership and cleanup, not physical stimulus timing qualification.
