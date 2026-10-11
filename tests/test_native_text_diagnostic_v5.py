"""Unqualified text fixtures never establish native ending authority."""
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_native_text_v5 as f
from pal.native_call_v5 import NativeReturned
from pal.native_text_v5 import NativeTextBuffer

class DiagnosticSnapshotTests(unittest.TestCase):
    def buffer(self):return NativeTextBuffer(request_sha256=f.REQUEST,profile_sha256=f.PROFILE,attempt_ref=f.ATTEMPT,model_id='swe-2-high')
    def check(self,b,phase,text,chunks):
        value=b.unqualified_snapshot()
        self.assertIs(type(value),dict)
        self.assertEqual(value,{'version':'NATIVE-TEXT-DIAGNOSTIC/1','authority':'unqualified','phase':phase,
            'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'utf8_bytes':len(text.encode()),
            'chunks':chunks,'request_sha256':f.REQUEST,'profile_sha256':f.PROFILE,
            'attempt_ref':f.ATTEMPT,'requested_model_id':'swe-2-high'})
        return value
    def test_before_begin_and_defensive_capture_are_observation_only(self):
        b=self.buffer();b.observe(f.chunk('ignored'));self.check(b,'not_begun','',0)
        b.begin();b.observe(f.chunk('日本'));b.observe(f.chunk(''));b.observe(f.chunk('語\n'))
        snapshot=self.check(b,'capturing','日本語\n',3);snapshot['attempt_ref']['run_id']='mutated';snapshot['text']='changed'
        self.check(b,'capturing','日本語\n',3);self.assertEqual(b.finish(f.receipt())['text'],'日本語\n')
    def test_strict_model_failure_retains_diagnostic_without_qualifying(self):
        for change in ({'effective_model':'other'},{'effective_model':None},{'effective_model_verified':False}):
            with self.subTest(change=change):
                b=self.buffer();b.begin();b.observe(f.chunk('valid partial 日本語'))
                with self.assertRaises(ValueError):b.finish(f.receipt(**change))
                snapshot=self.check(b,'capturing','valid partial 日本語',1)
                with self.assertRaises(ValueError):NativeReturned(capture=snapshot,cessation=f.receipt())
                with self.assertRaises(ValueError):b.finish(snapshot)
    def test_sealed_snapshot_does_not_reopen_or_change_capture(self):
        b=self.buffer();b.begin();b.observe(f.chunk('sealed'));original=b.finish(f.receipt())
        self.check(b,'sealed','sealed',1)
        with self.assertRaises(ValueError):b.observe(f.chunk('late'))
        with self.assertRaises(ValueError):b.finish(f.receipt())
        self.assertEqual(original['text'],'sealed');self.check(b,'sealed','sealed',1)
    def test_byte_chunk_and_utf8_poison_clear_valid_text(self):
        for kind in ('bytes','chunks','utf8'):
            with self.subTest(kind=kind):
                b=self.buffer();b.begin()
                if kind=='bytes':b.observe(f.chunk('x'*32768));self.check(b,'capturing','x'*32768,1);bad=f.chunk('x')
                elif kind=='chunks':
                    b.observe(f.chunk('x'))
                    for _ in range(2047):b.observe(f.chunk(''))
                    self.check(b,'capturing','x',2048);bad=f.chunk('')
                else:b.observe(f.chunk('valid'));bad=f.chunk('\ud800')
                with self.assertRaises(ValueError):b.observe(bad)
                self.check(b,'poisoned','',0)
                with self.assertRaises(ValueError):b.finish(f.receipt())

if __name__=='__main__':unittest.main()
