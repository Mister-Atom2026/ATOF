"""Wanted-level, fine and bribe mechanics used by :mod:`engine`.

The game engine keeps ``WantedLevel`` as the public type used by saves and the
game loop.  That class simply subclasses :class:`WantedState` from this module,
so the mechanics can be built and tested without importing pygame or the rest
of the engine.
"""

from __future__ import annotations

#: Highest achievable wanted level (number of "stars").
MAX_WANTED_LEVEL = 5
#: Price (₭) of removing a single wanted star with a bribe.
BRIBE_COST_PER_LEVEL = 400
#: Hard cap for a single outstanding fine (keeps saves sane).
MAX_FINE = 50_000


def _as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


class WantedState:
    """Track police attention, accumulated fines and bribe payments.

    ``level`` and ``escape_timer`` keep their original meaning from the old
    ``WantedLevel`` implementation.  ``fines`` is the total amount (₭) the
    player owes for crimes such as theft or property damage; it is paid off
    together with a bribe or separately via :meth:`pay_fine`.
    """

    MAX_LEVEL = MAX_WANTED_LEVEL
    BRIBE_COST_PER_LEVEL = BRIBE_COST_PER_LEVEL
    MAX_FINE = MAX_FINE

    def __init__(self, level=0, escape_timer=0, fines=0):
        self.level = self._clamp_level(level)
        self.escape_timer = max(0.0, float(escape_timer))
        self.fines = self._clamp_fine(fines)
        self.fine_reasons: list[str] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _clamp_level(cls, value) -> int:
        return max(0, min(cls.MAX_LEVEL, _as_int(value)))

    @classmethod
    def _clamp_fine(cls, value) -> int:
        return max(0, min(cls.MAX_FINE, _as_int(value)))

    @staticmethod
    def _timer_for_level(level: int) -> float:
        """Time (in simulated frames) needed to lose one star."""
        return 1800.0 + level * 600.0 if level else 0.0

    # ------------------------------------------------------------------
    # Crimes and fines
    # ------------------------------------------------------------------
    def add_fine(self, amount, reason: str = "") -> int:
        """Add a fine and return the amount actually added (never negative)."""
        added = self._clamp_fine(amount)
        if not added:
            return 0
        self.fines = self._clamp_fine(self.fines + added)
        if reason:
            self.fine_reasons.append(str(reason))
            self.fine_reasons[:] = self.fine_reasons[-5:]
        return added

    @property
    def total_fine(self) -> int:
        return self.fines

    def raise_level(self, amount: int = 1, fine=0, reason: str = "") -> int:
        """Raise the wanted level, optionally issuing a fine for the crime."""
        self.level = min(self.MAX_LEVEL, self.level + max(1, _as_int(amount, 1)))
        self.escape_timer = max(self.escape_timer, self._timer_for_level(self.level))
        if fine:
            self.add_fine(fine, reason)
        return self.level

    # ------------------------------------------------------------------
    # Costs and payments
    # ------------------------------------------------------------------
    def bribe_cost(self) -> int:
        """Cost (₭) of one bribe: one wanted star plus all unpaid fines."""
        return self.BRIBE_COST_PER_LEVEL * self.level + self.fines

    def bribe(self, money) -> tuple[bool, int]:
        """Try to bribe the police.

        On success the player loses one wanted star and all fines are cleared.
        Returns ``(success, amount_spent)``; no money is spent on failure.
        """
        cost = self.bribe_cost()
        if cost <= 0 or _as_int(money) < cost:
            return False, 0
        if self.level:
            self.level -= 1
            self.escape_timer = self._timer_for_level(self.level)
        self.fines = 0
        self.fine_reasons.clear()
        return True, cost

    def pay_fine(self, money) -> tuple[bool, int]:
        """Pay only the outstanding fine, keeping the wanted level.

        Returns ``(success, amount_spent)``.
        """
        cost = self.fines
        if cost <= 0 or _as_int(money) < cost:
            return False, 0
        self.fines = 0
        self.fine_reasons.clear()
        return True, cost

    # ------------------------------------------------------------------
    # Time / reset
    # ------------------------------------------------------------------
    def update(self, frame_scale: float, nearby_police: bool = False) -> None:
        if self.level == 0 or nearby_police:
            return
        self.escape_timer = max(0.0, self.escape_timer - frame_scale)
        if self.escape_timer == 0:
            self.level -= 1
            if self.level:
                self.escape_timer = self._timer_for_level(self.level)
            # Outstanding fines survive cooling off - they still have to be paid.

    def clear(self) -> None:
        """Fully reset wanted level, timer and fines (e.g. after being busted)."""
        self.level = 0
        self.escape_timer = 0.0
        self.fines = 0
        self.fine_reasons.clear()
