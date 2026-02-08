"""
flytrap_gate.py — Bio-inspired temporal gating state machine.

Models a "venus-flytrap-inspired" activation policy for cooling control:

    IDLE → PRIMED → OPEN → REFRACTORY → IDLE

State transitions:
    IDLE:        Counting trigger events within a sliding window.
                 If N_trigger events occur within T_window steps → PRIMED.
    PRIMED:      Gate opens on next update call → OPEN.
    OPEN:        Gate stays open while triggers continue.
                 When trigger stops → REFRACTORY.
    REFRACTORY:  Gate closed for T_refractory steps (cooldown).
                 After cooldown → IDLE.

Gate output is binary: 1 (open) or 0 (closed).
Chatter = number of transitions into OPEN state (i.e., closed→open edges).

No external dependencies. Pure Python.
"""

from __future__ import annotations

from collections import deque

from src.constants import GATE_N_TRIGGER, GATE_T_WINDOW, GATE_T_REFRACTORY


class FlyTrapGate:
    """Bio-inspired temporal gating policy.

    Parameters
    ----------
    N_trigger : int
        Number of trigger events required within T_window to open the gate.
    T_window : int
        Sliding window size (timesteps) for counting trigger events.
    T_refractory : int
        Cooldown period (timesteps) after gate closes before it can reopen.
    """

    STATES = ("IDLE", "PRIMED", "OPEN", "REFRACTORY")

    def __init__(
        self,
        N_trigger: int = GATE_N_TRIGGER,
        T_window: int = GATE_T_WINDOW,
        T_refractory: int = GATE_T_REFRACTORY,
    ) -> None:
        self.N_trigger = N_trigger
        self.T_window = T_window
        self.T_refractory = T_refractory

        self._state: str = "IDLE"
        self._trigger_times: deque[int] = deque()
        self._refractory_start: int = -1
        self._transition_count: int = 0  # closed→open edges (= chatter)

    def update(self, trigger: bool, t_now: int) -> bool:
        """Advance the state machine by one timestep.

        Parameters
        ----------
        trigger : bool
            Whether a trigger event occurred this timestep
            (e.g., PID output exceeds threshold).
        t_now : int
            Current timestep index.

        Returns
        -------
        gate_open : bool
            True if gate is open (output = 1), False if closed (output = 0).
        """
        # Record trigger events in sliding window
        if trigger:
            self._trigger_times.append(t_now)

        # Expire old events outside the window
        while self._trigger_times and self._trigger_times[0] < t_now - self.T_window:
            self._trigger_times.popleft()

        n_recent = len(self._trigger_times)

        if self._state == "IDLE":
            if n_recent >= self.N_trigger:
                self._state = "PRIMED"
            return False

        elif self._state == "PRIMED":
            self._state = "OPEN"
            self._transition_count += 1
            return True

        elif self._state == "OPEN":
            if not trigger:
                # Trigger stopped → begin refractory
                self._state = "REFRACTORY"
                self._refractory_start = t_now
                return False
            return True

        elif self._state == "REFRACTORY":
            elapsed = t_now - self._refractory_start
            if elapsed >= self.T_refractory:
                self._state = "IDLE"
                self._trigger_times.clear()
            return False

        return False  # defensive fallback

    @property
    def state(self) -> str:
        """Current state name."""
        return self._state

    @property
    def transition_count(self) -> int:
        """Number of closed→open transitions (chatter count)."""
        return self._transition_count

    def reset(self) -> None:
        """Reset all internal state."""
        self._state = "IDLE"
        self._trigger_times.clear()
        self._refractory_start = -1
        self._transition_count = 0
