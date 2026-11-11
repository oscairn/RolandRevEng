"""Inventory the three oscillator controls with ambiguous arithmetic arity."""
from functools import partial

from line_mix_variation import main
from quantizer_context_inventory import scan


if __name__ == '__main__':
    main(partial(scan, controls=(0x3074, 0x2d64, 0x0c3b)), __doc__)
