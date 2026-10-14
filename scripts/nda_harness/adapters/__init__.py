"""Adding a harness requires one adapter and one registry entry, not engine edits."""
from .codex import CodexAdapter
from .cursor import CursorAdapter

REGISTRY = {"codex": CodexAdapter(), "cursor": CursorAdapter()}
