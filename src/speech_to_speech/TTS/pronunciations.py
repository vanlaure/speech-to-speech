"""Respell words for the speech synthesiser only.

A pronunciation lexicon applied to the text just before it is synthesised (see
TTS/pocket_tts_handler.py). The transcript, the conversation history and the model's
own output are untouched: only the sound that comes out of the speaker changes.

Why it exists: a TTS voice cannot be told how to say a name. Respelling the word in
the *model's* text makes the transcript read wrong; respelling it here, after the text
has been recorded, does not. Example: the name "Jean" said the French way ("zhahn")
is obtained with {"Jean": "Zhahn"}.

The lexicon is a JSON object, word -> spelling, at
    ~/.config/atlas-voice/pronunciations.json     (override: $ATLAS_PRONUNCIATIONS)
and is re-read whenever the file changes, so editing it needs no restart. With no
file, nothing is changed. Matches are whole words and case-sensitive, so "Jean" is
respelled but "jeans" is not.
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

PATH = os.path.expanduser(os.environ.get("ATLAS_PRONUNCIATIONS", "~/.config/atlas-voice/pronunciations.json"))

DEFAULTS: dict = {}   # no built-in words; the lexicon file carries them

_cache: dict = {"mtime": None, "rules": None}


def _compile(lexicon: dict) -> list[tuple[re.Pattern, str]]:
    # Longest word first, so "Valjean" is not half-eaten by a shorter entry.
    return [
        (re.compile(r"\b" + re.escape(word) + r"\b"), str(spoken))
        for word, spoken in sorted(lexicon.items(), key=lambda kv: -len(kv[0]))
        if word and spoken
    ]


def _rules() -> list[tuple[re.Pattern, str]]:
    try:
        mtime = os.path.getmtime(PATH)
    except OSError:
        mtime = None
    if _cache["rules"] is None or mtime != _cache["mtime"]:
        lexicon = DEFAULTS
        if mtime is not None:
            try:
                with open(PATH, encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    lexicon = loaded
            except (OSError, ValueError):
                logger.warning("could not read %s; using no lexicon", PATH)
        _cache["mtime"], _cache["rules"] = mtime, _compile(lexicon)
    return _cache["rules"]


def apply(text: str) -> str:
    """The text as it should be *spoken*. Never raises: a bad lexicon must not silence the voice."""
    try:
        for pattern, spoken in _rules():
            text = pattern.sub(spoken, text)
    except Exception:
        logger.exception("pronunciation lexicon failed; speaking the text unchanged")
    return text