#!/usr/bin/env python

import simpy_events
import pep8
import pathlib

def test_pep8_conformance():
    """Test that we conform to PEP8."""
    pep8style = pep8.StyleGuide(prefix='E')
    base = pathlib.Path(simpy_events.__file__).parent
    result = pep8style.check_files(map(str, [
        base,
        # base / 'subdir',
    ]))
    assert result.total_errors == 0
