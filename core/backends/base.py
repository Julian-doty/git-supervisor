"""
Backend interface both entry scripts talk to. Adding a third backend later
(another cloud API, a different local runtime) means writing one class here
that implements `generate` — nothing in core/ or the entry scripts needs to
change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Backend(ABC):
    """
    A backend already knows its own persona/system prompt (bound at
    construction) and its own sampling settings. Callers only ever pass the
    task-specific prompt built by the entry script (the SEARCH_QUERY or
    REPO_ANALYSIS prompt) and get back the raw text response.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send `prompt` to the model and return its raw text response."""
        raise NotImplementedError

    @property
    @abstractmethod
    def label(self) -> str:
        """Short human-readable identifier for status output, e.g. 'ollama:git-supervisor'."""
        raise NotImplementedError
