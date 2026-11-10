"""An original stereo one-pole filter built from checked BMC packet profiles."""
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment


def programs():
    """Generate two profiles whose state buffers alternate between samples."""
    first, second = [0, 1], [2, 3]
    return tuple(assemble_fragment(dict(kind='dry_wet_tail_with_scratch',
                                        wet_addresses=read, scratch_addresses=write,
                                        coefficient_slots=[0, 1, 2, 3]))
                 for read, write in ((first, second), (second, first)))


def filter_frames(frames, feedback):
    """Process stereo frames with one previous output per channel and a zero initial state."""
    if (isinstance(feedback, bool) or not isinstance(feedback, (int, float))
            or not 0 <= feedback < 1):
        raise ValueError('Expected feedback in [0, 1)')
    variants = programs()
    data = {0: 0.0, 1: 0.0}
    coefficients = {0: 1-feedback, 1: feedback, 2: 1, 3: 1}
    output = []
    for index, (left, right) in enumerate(frames):
        result = execute_fragment(variants[index % 2], data, coefficients,
                                  {0x2016: left, 0x2017: right})
        data = result['data']
        output.append((result['ports'][0], result['ports'][4]))
    return output
