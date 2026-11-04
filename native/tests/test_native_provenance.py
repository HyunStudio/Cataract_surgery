"""Quoted local include dependencies must travel with numerical build proofs."""
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from native_build_provenance import source_hashes


class ProvenanceTests(unittest.TestCase):
    def fixture(self):
        # Keep tiny generated inputs under ignored .tools; no recursive cleanup.
        path=Path(tempfile.mkdtemp(prefix='provenance-test-',dir=ROOT/'.tools'))
        self.assertEqual(path.resolve().parent,(ROOT/'.tools').resolve())
        return path

    def test_transitive_local_headers_and_cycles(self):
        folder=self.fixture();entry=folder/'entry.cpp';first=folder/'a.h';last=folder/'b.h'
        entry.write_text('#include "a.h"\n#include <vector>\n');first.write_text('#include "b.h"\n');last.write_text('#include "a.h"\n#define VALUE 1\n')
        before=source_hashes([entry])
        self.assertEqual(set(before),{str(p.relative_to(ROOT)) for p in (entry,first,last)})
        last.write_text('#include "a.h"\n#define VALUE 2\n')
        after=source_hashes([entry])
        self.assertNotEqual(before[str(last.relative_to(ROOT))],after[str(last.relative_to(ROOT))])

    def test_quoted_dependency_cannot_leave_workspace(self):
        folder=self.fixture();entry=folder/'entry.cpp'
        entry.write_text('#include "'+str(ROOT.parent/'not-in-workspace.h').replace('\\','/')+'"\n')
        with self.assertRaises(ValueError):source_hashes([entry])


if __name__=='__main__':unittest.main()
