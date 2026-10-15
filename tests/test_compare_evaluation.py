from pathlib import Path
import math

import pytest

from analysis.compare_evaluation import parse_filename


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (
            "bearing_wear_proxy_adaptive.csv",
            ("bearing_wear_proxy", "adaptive", "standard"),
        ),
        (
            "combined_supported_baseline.csv",
            ("combined_supported", "baseline", "standard"),
        ),
        (
            "cooling_failure_constrained_800s.csv",
            ("cooling_failure", "constrained", "standard"),
        ),
        (
            "sensor_bias_adaptive_600s_basyx.csv",
            ("sensor_bias", "adaptive", "basyx"),
        ),
        (
            "combined_constrained_controller_only.csv",
            ("combined", "constrained", "controller_only"),
        ),
        (
            "combined_constrained_basyx_800s.csv",
            ("combined", "constrained", "basyx"),
        ),
    ],
)
def test_parse_campaign_and_variant_filenames(filename, expected):
    scenario, controller, variant, _ = parse_filename(Path(filename))

    assert (scenario, controller, variant) == expected


@pytest.mark.parametrize(
    "filename",
    [
        "comparison.csv",
        "bearing_wear_proxy_adaptive_metrics.csv",
        "combined_constrained_detail.csv",
    ],
)
def test_parse_filename_skips_non_experiment_csvs(filename):
    parsed = parse_filename(Path(filename))

    assert parsed[:3] == (None, None, None)
    assert math.isnan(parsed[3])