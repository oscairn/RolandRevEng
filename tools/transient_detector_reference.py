"""Finite native TRANSIENT detector arithmetic; no BMC instructions are executed."""
import math

from line_shaping_study import EPSILON, _finite
from oscillator_phase_study import normalize_phase_sum

HISTORY = (18, 20, 22, 24, 26, 30, 32, 35)
DEFAULTS = (8, 0x18, 0x28, 0x78, 0xc8, 0xd8, 0xe8)
ZERO_LOG = float.fromhex('-0x1.62e42fefa39efp+4')
LOG_LIMIT = float.fromhex('-0x1.ba18a998fffa0p+2')


def detector_step(left, right, history, defaults):
    """Return retained logical writes and decisions for one finite native frame."""
    if not hasattr(math, 'fma'):
        raise ValueError('TRANSIENT detector requires Python 3.13+ math.fma')
    if not isinstance(history, dict) or not isinstance(defaults, dict):
        raise ValueError('Expected TRANSIENT history/default dictionaries')
    left, right = map(_finite, (left, right))
    try:
        past = {key: _finite(history[key]) for key in HISTORY}
        values = {key: _finite(defaults[key]) for key in DEFAULTS}
    except KeyError as error:
        raise ValueError('Missing TRANSIENT history or constructor defaults') from error
    if values[0x28] <= 0:
        raise ValueError('Expected positive peak normalization')
    # FCSEL GE retains negative zero; the following GT tie selects the right input.
    magnitude_left = left if left >= 0 else -left
    magnitude_right = right if right >= 0 else -right
    magnitude = magnitude_left if magnitude_left > magnitude_right else magnitude_right
    peak = _finite(values[0x28]*magnitude)
    logarithm = ZERO_LOG if peak == 0 else math.log(peak)
    delta = _finite(logarithm-past[18])
    clamped = logarithm if logarithm > values[8] else values[8]
    held = clamped if clamped > past[18] else past[18]
    reset = delta >= EPSILON
    if reset:
        phase, guard = -1.0, -2.0
    else:
        phase_sum = _finite(past[20]+values[0x18])
        guard = _finite(phase_sum-1.0)
        phase = normalize_phase_sum(phase_sum)
    best = past[22] if past[22] > past[24] else past[24]
    best = best if best > held else held
    roll = guard <= -EPSILON
    if roll:
        first_copy, second_copy, next_window = past[24], past[26], past[22]
        best = best if best > past[26] else past[26]
    else:
        first_copy, second_copy, next_window = past[22], past[24], held
        held = logarithm
    limited_log = logarithm if logarithm > LOG_LIMIT else LOG_LIMIT
    decayed = _finite(past[30]+values[0x78])
    release = decayed if decayed > limited_log else limited_log
    rate_field = 0xe8 if _finite(release-LOG_LIMIT) < EPSILON else 0xd8
    decayed = _finite(past[32]+values[rate_field])
    second_release = decayed if decayed > limited_log else limited_log
    try:
        smooth = _finite(math.fma(_finite(best-past[35]), values[0xc8], past[35]))
    except OverflowError as error:
        raise ValueError('TRANSIENT smoothing exceeds the finite reference domain') from error
    rising = best if best < smooth else smooth
    writes = {0: peak, 1: logarithm, 17: held, 19: phase, 21: next_window,
              23: first_copy, 25: second_copy, 27: best, 2: best,
              29: release, 31: second_release, 33: best, 34: rising,
              36: _finite(rising-best), 37: _finite(release-second_release)}
    return dict(writes=writes, phase_reset=reset, history_roll=roll,
                retained_phase_guard=guard, release_rate_field=rate_field)
