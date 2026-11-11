import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import swap_words
from program_write_study import active_drain_plan, completion_plan, write_geometry


def replay(plan, stored, address, count):
    memory = bytearray(b'\xa5'*(count+4))
    for step in plan['steps']:
        source = step['source_offset']; size = step['source_read_bytes']
        value = stored[source:source+size]
        if len(value) != size:
            raise ValueError('Source read exceeds backing buffer')
        if step['kind'] == 'raw_head':
            value = int.from_bytes(value, 'little').to_bytes(2, 'big')
        elif step['kind'] == 'raw_tail':
            value = (int.from_bytes(value, 'little') >> 16).to_bytes(2, 'big')
        else:
            value = swap_words(value)
        offset = step['destination']-address+2
        memory[offset:offset+len(value)] = value
    return memory


class GeometryTests(unittest.TestCase):
    def test_both_destination_alignments_every_even_length_and_neighbour_canaries(self):
        for address in (0x4020, 0x4022):
            for count in range(0, 132, 2):
                logical = bytes((7+13*index)&255 for index in range(count))
                prefix = bytes(address & 2) if count else b''
                padded = prefix+logical
                stored = swap_words(padded+bytes(-len(padded)%4))
                plan = write_geometry(4, address, count)
                self.assertEqual(len(stored), plan['stored_buffer_bytes'])
                self.assertEqual(sum(step['byte_count'] for step in plan['steps']), count)
                self.assertEqual(replay(plan, stored, address, count), b'\xa5\xa5'+logical+b'\xa5\xa5')
                self.assertFalse(plan['execution_ready'])

    def test_shaped_voice_tail_first_dma_extent_and_padding_are_distinct(self):
        import bmc_filtered_voice as filtered
        logical = b''.join(filtered.programs(True)); stored = filtered.storage_program(True)
        plan = write_geometry(4, 0x4020, len(logical))
        self.assertEqual(plan['stored_buffer_bytes'], 512)
        self.assertEqual(plan['actual_source_read_extent'], 512)
        self.assertEqual([step['kind'] for step in plan['steps']], ['raw_tail', 'dma_queue'])
        self.assertEqual([step['byte_count'] for step in plan['steps']], [2, 508])
        self.assertEqual(plan['steps'][0]['destination'], 0x421c)
        self.assertEqual(plan['steps'][0]['source_offset'], 508)
        self.assertEqual(replay(plan, stored, 0x4020, 510), b'\xa5\xa5'+logical+b'\xa5\xa5')
        self.assertRaises(ValueError, replay, plan, stored[:-2], 0x4020, 510)
        # Passing padded size as the byte count writes the padding into the destination.
        padded = write_geometry(4, 0x4020, 512)
        self.assertEqual(replay(padded, stored, 0x4020, 512)[-4:-2], b'\0\0')

    def test_halfword_start_requires_prefix_and_can_read_more_than_payload(self):
        plan = write_geometry(4, 0x4022, 4)
        self.assertEqual((plan['logical_source_prefix_bytes'], plan['stored_buffer_bytes'],
                          plan['actual_source_read_extent']), (2, 8, 8))
        wrong = swap_words(bytes.fromhex('11223344'))
        self.assertRaises(ValueError, replay, plan, wrong, 0x4022, 4)
        short = write_geometry(4, 0x4022, 2)
        self.assertEqual((short['stored_buffer_bytes'], short['actual_source_read_extent']), (4, 2))

    def test_dma_threshold_after_edges_and_descriptor_bounds(self):
        for address, size, expected in ((0x4020, 62, 'cpu_copy'), (0x4020, 64, 'dma_queue'),
                                        (0x4022, 64, 'cpu_copy'), (0x4022, 66, 'dma_queue')):
            self.assertEqual(write_geometry(4, address, size)['steps'][-1]['kind'], expected)
        limit = 0xfff*4
        for count, sizes in ((limit, [limit]), (limit+4, [limit, 4])):
            result = write_geometry(4, 0, count)['dma_descriptors']
            self.assertEqual([item['byte_count'] for item in result], sizes)
            self.assertEqual(result[-1]['source_offset'], sum(sizes[:-1]))
        self.assertEqual(len(write_geometry(4, 0, limit*32)['dma_descriptors']), 32)
        self.assertRaises(ValueError, write_geometry, 4, 0, limit*32+4)
        for args in ((True, 0, 0), (7, 0, 0), (4, 1, 2), (4, 0, 1),
                     (4, -2, 0), (4, 0, True), (4, 0xfffffffe, 2), (4, 0x80000, 2)):
            self.assertRaises(ValueError, write_geometry, *args)


class CompletionTests(unittest.TestCase):
    def test_separate_drain_only_handles_started_dma_and_accepts_existing_event(self):
        for state in (0, 1):
            result = active_drain_plan(state, 0xa4)
            self.assertFalse(result['starts_queue'])
            self.assertFalse(result['waits'])
            self.assertEqual(result['state_on_return'], state)
        for flags in (0xa0, 0xa4):
            result = active_drain_plan(2, flags)
            self.assertTrue(result['waits'])
            self.assertEqual(result['state_on_return'], 0)
            self.assertEqual(result['event_flags_on_return'], 0xa0)
            self.assertEqual(result['return_requires_new_completion_event'], not bool(flags & 4))
            self.assertFalse(result['completion_proven'])
        for args in ((True,), (3,), (2, -1)):
            self.assertRaises(ValueError, active_drain_plan, *args)

    def test_nonwaiting_start_cannot_be_drained_by_calling_this_helper_again(self):
        start = completion_plan(1, False, 0xa4)
        self.assertTrue(start['starts_queue']); self.assertFalse(start['waits'])
        self.assertEqual(start['event_flags_before_start'], 0xa0)
        self.assertEqual(start['state_on_return'], 2)
        # The IRQ merely sets event4; state2 still takes the immediate-return path.
        later = completion_plan(2, True, 0xa4)
        self.assertFalse(later['starts_queue']); self.assertFalse(later['waits'])
        self.assertEqual(later['state_on_return'], 2)
        self.assertEqual(later['event_flags_on_return'], 0xa4)
        wait = completion_plan(1, True, 0xa4)
        self.assertTrue(wait['waits']); self.assertEqual(wait['state_on_return'], 0)
        self.assertTrue(wait['return_requires_new_completion_event'])
        self.assertEqual(wait['event_flags_on_return'], 0xa0)
        self.assertFalse(wait['completion_proven'])
        for state in (0, 2):
            for flag in (False, True):
                self.assertFalse(completion_plan(state, flag)['waits'])
        for args in ((True, True), (3, True), (1, 1), (1, True, -1)):
            self.assertRaises(ValueError, completion_plan, *args)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS, 'Pinned Fantom CORE1 and Capstone required')
class CorpusTests(unittest.TestCase):
    def test_real_edge_completion_queue_and_callback_anchors(self):
        from core1 import Core1
        from program_write_study import report
        core = Core1(CORPUS/'b0c1a.bin')
        result = report(core)
        self.assertFalse(result['start_then_later_wait_drains'])
        self.assertFalse(result['callback_resets_state'])
        self.assertEqual(result['active_drain_helper'], 0x112f508)
        self.assertEqual(result['manager_start_slot'], 0x44)
        self.assertEqual(result['manager_drain_slot'], 0x48)
        self.assertEqual(result['examples'][0]['actual_source_read_extent'], 512)
        self.assertFalse(result['execution_ready'])
        core.data += b'changed'
        self.assertRaises(ValueError, report, core)

    def test_changed_completion_early_return_is_rejected(self):
        from core1 import Core1
        from program_write_study import report
        from dramio_owner_study import expect
        core = Core1(CORPUS/'b0c1a.bin')
        def changed(core, address, mnemonic, operands):
            return expect(core, address, mnemonic, '#wrong' if address == 0x112f6b0 else operands)
        with patch('dramio_owner_study.expect', side_effect=changed):
            self.assertRaises(ValueError, report, core)


if __name__ == '__main__':
    unittest.main()
