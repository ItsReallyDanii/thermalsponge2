"""
pid_controller.py — Discrete PID controller with anti-windup clamping.

Provides a standard PID baseline for thermal orchestration experiments.
Includes Ziegler-Nichols closed-loop auto-tuning from ultimate gain/period.

No external dependencies beyond Python stdlib.
"""

from __future__ import annotations


class PIDController:
    """Discrete PID controller with output clamping and integral anti-windup.

    The controller computes:
        e(t) = setpoint - measured
        u(t) = clamp(Kp*e + Ki*integral(e) + Kd*derivative(e), u_min, u_max)

    Anti-windup: integral accumulation is frozen when output is saturated
    and the integral term would push further into saturation.
    """

    def __init__(
        self,
        Kp: float,
        Ki: float,
        Kd: float,
        dt: float,
        setpoint: float,
        u_min: float = 0.0,
        u_max: float = 1.0,
    ) -> None:
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.setpoint = setpoint
        self.u_min = u_min
        self.u_max = u_max

        self._integral = 0.0
        self._prev_error = 0.0
        self._first_step = True

    def step(self, measured: float) -> float:
        """Compute control output from measured process variable.

        Parameters
        ----------
        measured : current process variable (e.g., T_max_chip).

        Returns
        -------
        u : control signal in [u_min, u_max].
        """
        error = self.setpoint - measured

        # Proportional
        p_term = self.Kp * error

        # Integral (trapezoidal rule) with anti-windup
        candidate_integral = self._integral + error * self.dt
        i_term = self.Ki * candidate_integral

        # Derivative (backward difference, skip first step)
        if self._first_step:
            d_term = 0.0
            self._first_step = False
        else:
            d_term = self.Kd * (error - self._prev_error) / self.dt

        # Raw output
        u_raw = p_term + i_term + d_term

        # Clamp
        u = max(self.u_min, min(self.u_max, u_raw))

        # Anti-windup: only accumulate integral if not saturated,
        # or if integral is moving away from saturation
        saturated_high = u_raw > self.u_max and error > 0
        saturated_low = u_raw < self.u_min and error < 0
        if not (saturated_high or saturated_low):
            self._integral = candidate_integral

        self._prev_error = error
        return u

    def reset(self) -> None:
        """Zero all internal state."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._first_step = True

    @staticmethod
    def auto_tune_zn(
        Ku: float,
        Tu: float,
        dt: float,
        setpoint: float,
    ) -> "PIDController":
        """Ziegler-Nichols closed-loop tuning from ultimate gain and period.

        Parameters
        ----------
        Ku : ultimate gain (gain at which system oscillates).
        Tu : ultimate period (period of sustained oscillation).
        dt : controller timestep.
        setpoint : desired process variable setpoint.

        Returns
        -------
        Configured PIDController with ZN-classic PID gains:
            Kp = 0.6 * Ku
            Ki = 1.2 * Ku / Tu
            Kd = 0.075 * Ku * Tu
        """
        Kp = 0.6 * Ku
        Ki = 1.2 * Ku / Tu
        Kd = 0.075 * Ku * Tu
        return PIDController(Kp=Kp, Ki=Ki, Kd=Kd, dt=dt, setpoint=setpoint)
