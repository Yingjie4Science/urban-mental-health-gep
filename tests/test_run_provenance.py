import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_provenance


class ProvenanceTests(unittest.TestCase):
    def test_manifest_records_exact_input_and_output_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            project = root / 'project'
            source.mkdir()
            project.mkdir()
            (source / 'script.py').write_text('print(1)\n', encoding='utf-8')
            (root / 'input.csv').write_bytes(b'abc')
            (project / 'result.csv').write_bytes(b'42')
            with patch.object(run_provenance, 'SOURCE_FILES', ('script.py',)), \
                 patch.object(run_provenance, 'git_head', return_value=None):
                path = run_provenance.write_manifest(
                    project_dir=project,
                    inputs={'test_input': root / 'input.csv'},
                    source_dir=source,
                    outputs={'result': project / 'result.csv'},
                    parameters={'p0': 0.115},
                )
            record = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(record['inputs']['test_input']['sha256'], hashlib.sha256(b'abc').hexdigest())
            self.assertEqual(record['outputs']['result']['size_bytes'], 2)
            self.assertEqual(record['parameters']['p0'], 0.115)


if __name__ == '__main__':
    unittest.main()
