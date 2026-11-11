"""Finite native TRANSIENT exp/smoothing and final gain reference kernels."""
import math

from line_shaping_study import EPSILON, _finite, _float32


def envelope_step(argument, previous, *, above, below):
    if not hasattr(math, 'fma'):
        raise ValueError('TRANSIENT smoothing requires Python 3.13+ math.fma')
    argument, previous, above, below = map(_finite, (argument, previous, above, below))
    try:
        delta = _finite(math.exp(argument)-previous)
    except OverflowError as error:
        raise ValueError('TRANSIENT exponential exceeds the finite reference domain') from error
    return _finite(math.fma(delta, above if delta > -EPSILON else below, previous))


def tail_reference(left, right, first, second, coefficients):
    if not hasattr(math, 'fma'):
        raise ValueError('TRANSIENT gain requires Python 3.13+ math.fma')
    if not isinstance(coefficients, (tuple, list)) or len(coefficients) != 4:
        raise ValueError('Expected four live coefficient values')
    master, c1, c2, c3 = map(_float32, coefficients)
    left, right, first, second = map(_finite, (left, right, first, second))
    product = _finite(first*second)
    difference = _finite(first-product)
    gain = _finite(math.fma(difference, c3, math.fma(1-first, c1, product*c2)+1))
    return dict(gain=gain, output=(_finite((left*gain)*master), _finite((right*gain)*master)))
