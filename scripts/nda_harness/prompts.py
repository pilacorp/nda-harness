"""Keyboard selections with a numbered fallback for limited terminals."""
import os
import sys


def _keyboard(screen, title, choices, multiple):
    import curses
    curses.curs_set(0)
    screen.keypad(True)
    focused, selected, error = 0, set(), ""
    while True:
        height, width = screen.getmaxyx()
        if (height < len(choices) + 5 or width < 40
                or any(len(label) + (4 if multiple else 0) >= width for _, label in choices)):
            raise curses.error("Terminal too small")
        screen.erase()
        screen.addnstr(0, 0, title, width - 1)
        help_text = "Up/Down: move; Space: toggle; Enter: confirm" if multiple else "Up/Down: move; Enter: confirm"
        screen.addnstr(1, 0, help_text, width - 1)
        for index, (_, label) in enumerate(choices):
            marker = ("[x] " if index in selected else "[ ] ") if multiple else ""
            screen.addnstr(index + 3, 0, marker + label, width - 1,
                           curses.A_REVERSE if index == focused else curses.A_NORMAL)
        screen.addnstr(len(choices) + 4, 0, error, width - 1)
        screen.refresh()
        key = screen.getch()
        if key in (3, 27):
            raise KeyboardInterrupt
        if key == 4:
            raise EOFError
        if key == curses.KEY_UP:
            focused = (focused - 1) % len(choices)
        elif key == curses.KEY_DOWN:
            focused = (focused + 1) % len(choices)
        elif key == ord(" ") and multiple:
            selected.symmetric_difference_update({focused})
        elif key in (10, 13, curses.KEY_ENTER):
            if not multiple:
                return [choices[focused][0]]
            if selected:
                return [value for index, (value, _) in enumerate(choices) if index in selected]
            error = "Select at least one agent with Space."


def _numbered(title, choices, multiple):
    print(title, file=sys.stderr)
    for index, (_, label) in enumerate(choices, 1):
        print(f"  {index}. {label}", file=sys.stderr)
    while True:
        print("Select numbers separated by commas: " if multiple else "Select one number: ",
              end="", file=sys.stderr, flush=True)
        raw = input().strip()
        try:
            numbers = [int(part.strip()) for part in raw.split(",")]
            if (not multiple and len(numbers) != 1) or any(number < 1 or number > len(choices) for number in numbers):
                raise ValueError()
            return [value for index, (value, _) in enumerate(choices, 1) if index in numbers]
        except ValueError:
            print("Choose valid menu numbers; an empty selection is not allowed.", file=sys.stderr)


def select_options(title, choices, multiple=False):
    if not sys.stdin.isatty():
        raise ValueError("Interactive selection requires a terminal; supply --agents and --scope.")
    selected = None
    if sys.stdout.isatty() and os.environ.get("TERM") not in (None, "", "dumb"):
        try:
            import curses
        except ImportError:
            pass
        else:
            try:
                selected = curses.wrapper(_keyboard, title, choices, multiple)
            except (curses.error, OSError):
                pass
    if selected is None:
        selected = _numbered(title, choices, multiple)
    labels = dict(choices)
    print(f"{title}: " + ", ".join(labels[value] for value in selected), file=sys.stderr)
    return selected
