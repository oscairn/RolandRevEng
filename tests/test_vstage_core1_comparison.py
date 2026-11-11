import importlib.util
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from bmc_dsp import packets
from bmc_subset import assemble_fragment
from fdrv_cascade_study import cascade_spec,FIXTURE_COEFFICIENTS
from fdrv_post_cubic_study import post_mix_spec
from vstage_core1_comparison import body_hits,context_key,report


class ContextTests(unittest.TestCase):
    def test_structural_scanner_does_not_require_native_plugin_image(self):
        with tempfile.TemporaryDirectory()as folder:
            subprocess.run([sys.executable,'-c',
                'import analyze,sys; assert "lib" not in sys.modules'],
                env={**os.environ,'BMC_CORPUS_DIR':folder,'PYTHONPATH':str(ROOT/'tools')},check=True)

    def test_indices_and_numeric_literals_do_not_create_contexts_but_extensions_and_tags_do(self):
        first=[w for _,w in packets(assemble_fragment(cascade_spec()))]
        changed=[w for _,w in packets(assemble_fragment(cascade_spec(0x100,FIXTURE_COEFFICIENTS)))]
        self.assertEqual(list(map(context_key,first)),list(map(context_key,changed)))
        ext=list(first[2]);ext[5]=0
        self.assertNotEqual(context_key(ext),context_key(first[2]))
        mix=[w for _,w in packets(assemble_fragment(post_mix_spec()))][3]
        slot=list(mix);slot[6]+=1
        self.assertEqual(context_key(slot),context_key(mix))
        tag=list(mix);tag[6]&=0xfff
        self.assertNotEqual(context_key(tag),context_key(mix))

    def test_body_match_requires_both_packet_boundaries(self):
        entries=[(dict(source_offset=32),b'aabcdd',{0,2,6})]
        self.assertEqual(body_hits(entries,b'bc'),[])
        self.assertEqual(body_hits(entries,b'abcdd'),[])
        self.assertEqual(body_hits(entries,b'bcdd'),[dict(source_offset=32,logical_byte_offset=2)])


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
UPDATE=CORPUS/'vstage-worker/VSTAGE_UPA.BIN'
HAS_CORPUS=importlib.util.find_spec('capstone')and UPDATE.exists()and(CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS,'Pinned V-STAGE and Fantom corpus required')
class CorpusTests(unittest.TestCase):
    def test_real_code_matches_offsets_failed_candidate_and_relocated_positive_controls(self):
        from core1 import Core1
        from edge_juno_firmware_study import update_parts
        from vstage_firmware_study import UPDATE_SHA256
        from vstage_core1_comparison import WINDOWS
        r=report(UPDATE,CORPUS/'b0c1a.bin')
        self.assertEqual((r['baseline']['framed_segments'],r['baseline']['distinct_contexts']),(377,5089))
        self.assertEqual([g['inventory']['framed_segments']for g in r['groups']],[619,578,81])
        self.assertEqual([len(g['inventory']['framing_failures'])for g in r['groups']],[0,1,0])
        self.assertEqual([g['unseen_context_count']for g in r['groups']],[1221,1336,1904])
        self.assertEqual([sorted(x['length']for x in g['shared_segments'])for g in r['groups']],
                         [[6,198,806,11572,51542],[6,198,11572],[6]])
        self.assertEqual([[len(w['hits'])for w in g['service_windows']]for g in r['groups']],
                         [[1,0,1],[1,0,1],[0,0,0]])
        parts=dict(update_parts(UPDATE,UPDATE_SHA256));fantom=Core1(CORPUS/'b0c1a.bin')
        with tempfile.TemporaryDirectory()as folder:
            for g in r['groups']:
                raw=parts[g['component']];path=Path(folder)/g['component'];path.write_bytes(raw);core=Core1(path)
                for window,(_,address,length)in zip(g['service_windows'],WINDOWS,strict=True):
                    expected=fantom.data[fantom.offset(address):fantom.offset(address)+length]
                    for hit in window['hits']:
                        self.assertEqual(raw[hit['container_offset']:hit['container_offset']+length],expected)
                        self.assertEqual(hit['container_offset'],core.header+core.offset(hit['runtime']))
                self.assertTrue(all(len(x['fantom_hits'])==1 for x in g['relocated_fdrv_body_checks']))
            positive=[x for x in r['groups'][1]['relocated_fdrv_body_checks']if x['vstage_hits']]
            self.assertEqual(len(positive),1)
            self.assertEqual(positive[0]['fantom_segment_base'],0x8040)
            bad=Path(folder)/'changed-fantom.bin'
            data=bytearray((CORPUS/'b0c1a.bin').read_bytes());data[-1]^=1;bad.write_bytes(data)
            self.assertRaises(ValueError,report,UPDATE,bad)
        self.assertFalse(r['new_opcode_meanings_proved'])
        self.assertFalse(r['owner_proven_inventory'])
        self.assertFalse(r['hardware_compatibility_verified'])


if __name__=='__main__':unittest.main()
