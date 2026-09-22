"""
Audio alert service for FocusFlow.
Plays gentle sound effects using Linux audio subsystems (pw-play, paplay, aplay).
"""

import shutil
import subprocess
import threading
import logging
from pathlib import Path
from typing import Optional

from focusflow.config import CHIME_PATH

logger = logging.getLogger(__name__)


class SoundPlayer:
    """Non-blocking, cross-desktop Linux audio player."""

    def __init__(self, default_chime: Optional[Path] = None):
        self.default_chime = Path(default_chime) if default_chime else CHIME_PATH
        self._player_bin = self._detect_player()

    def _detect_player(self) -> Optional[str]:
        """Find an available native Linux audio player."""
        for cmd in ("pw-play", "paplay", "aplay"):
            found = shutil.which(cmd)
            if found:
                return found
        return None

    def play_chime(self, sound_path: Optional[Path] = None):
        """Play the notification chime in a non-blocking background thread."""
        target = Path(sound_path) if sound_path else self.default_chime
        if not target.exists():
            logger.warning("Sound file not found: %s", target)
            return

        if not self._player_bin:
            logger.info("No audio player binary (pw-play/paplay/aplay) found.")
            return

        def _worker():
            try:
                subprocess.run(
                    [self._player_bin, str(target)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception as e:
                logger.debug("Failed playing sound via %s: %s", self._player_bin, e)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
