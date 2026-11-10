import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from factory_gate_study import literal_pointer_copy, report

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and importlib.util.find_spec('elftools')
                     and (CORPUS/'qctest').exists(), 'Recorded qctest and installed parsers required')
class CorpusTests(unittest.TestCase):
    def test_initializer_dispatch_and_separate_intro(self):
        result = report((CORPUS/'qctest').read_bytes())
        self.assertEqual(result['initializer_copies'], 34)
        self.assertEqual([g['count'] for g in result['groups']], [6, 21, 6])
        objects = {entry['object'] for group in result['groups'] for entry in group['entries']}
        self.assertEqual(len(objects), 28)
        self.assertNotIn(result['intro_object'], objects)
        self.assertNotIn(0x40751c, result['intro_virtual_methods'])
        self.assertEqual(len(result['indexed_group_loads']), 23)
        self.assertEqual(sum(row['field'] == 8 for row in result['indexed_group_loads']), 5)
        self.assertFalse(result['mode3_activation_proven'])
        self.assertFalse(result['all_aliases_resolved'])

    def test_pointer_copy_rejects_narrow_store(self):
        import capstone
        from elftools.elf.elffile import ELFFile
        with (CORPUS/'qctest').open('rb') as stream:
            elf = ELFFile(stream)
            text = elf.get_section_by_name('.text')
            offset = 0x406f58-text['sh_addr']
            original = text.data()[offset:offset+24]
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
        md.detail = True
        read = lambda address, size: (0x5e3f60).to_bytes(size, 'little')
        row = literal_pointer_copy(list(md.disasm(original, 0x406f58)), read)
        self.assertEqual(row['destination'], 0x5e3f58)
        changed = bytearray(original)
        changed[-1] ^= 0x40  # STR x1 becomes STR w1: no longer an eight-byte pointer copy.
        with self.assertRaises(ValueError):
            literal_pointer_copy(list(md.disasm(changed, 0x406f58)), read)


if __name__ == '__main__':
    unittest.main()
