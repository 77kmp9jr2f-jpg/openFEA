"""Support deposition must not inflate the model-only mass comparison."""
import pytest

from scripts.compare_slicer_usage import extrusion, deposition_totals


GCODE = '''M83
; FEATURE: Outer wall
G1 X1 Y0 E2
G1 E-1
G1 E1
; FEATURE: Support
G1 X2 Y1 E3
; FEATURE: Support interface
G1 X3 Y1 E1
'''


def test_model_only_parser_rejects_supports_by_default():
    with pytest.raises(ValueError, match='Support'):
        extrusion(GCODE)


def test_support_mass_stays_separate_from_part_mass():
    roles = extrusion(GCODE, include_support=True)
    assert deposition_totals(roles) == {'model_mm': 2, 'support_mm': 4, 'total_mm': 6}


def test_support_mode_still_rejects_unaccounted_custom_extrusion():
    with pytest.raises(ValueError, match='Custom'):
        extrusion(GCODE + '; FEATURE: Custom\nG1 X4 E5\n', include_support=True)
