"""Diagnostic evidence must preserve its source and describe the current input."""
import hashlib
import json
import os

import pytest

from backend.stl_io import write_box_stl
from scripts.validate_original_stl import validate


def test_output_hard_link_cannot_overwrite_source(tmp_path):
    source, output = tmp_path/'source.stl', tmp_path/'report.json'
    write_box_stl(source)
    original = source.read_bytes()
    os.link(source, output)
    with pytest.raises(ValueError, match='overwrite'):
        validate(source, output)
    assert source.read_bytes() == original


def test_malformed_input_replaces_prior_success_evidence(tmp_path):
    valid, malformed, output = tmp_path/'valid.stl', tmp_path/'bad.stl', tmp_path/'report.json'
    write_box_stl(valid)
    assert validate(valid, output)
    raw = b'not an STL'
    malformed.write_bytes(raw)
    assert not validate(malformed, output)
    record = json.loads(output.read_text())
    assert record['source_sha256'] == hashlib.sha256(raw).hexdigest()
    assert record['source_unchanged']
    assert not record['production_import']['accepted']
    assert 'STL' in record['production_import']['error']
    assert record['experimental_probes'] == []
