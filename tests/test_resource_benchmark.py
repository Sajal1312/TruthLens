"""Pure offline checks for resource-benchmark reporting helpers."""
import pytest

from evaluation.benchmark_resources import _latency_summary, _normalize_peak_rss_bytes


def test_peak_rss_unit_conversion_is_platform_specific():
    assert _normalize_peak_rss_bytes(4096, "darwin") == 4096
    assert _normalize_peak_rss_bytes(4, "linux") == 4096


def test_latency_summary_reports_repeated_measurements_in_milliseconds():
    summary = _latency_summary([0.01, 0.02, 0.03])
    assert summary["sample_count"] == 3
    assert summary["min_ms"] == pytest.approx(10)
    assert summary["median_ms"] == pytest.approx(20)
    assert summary["mean_ms"] == pytest.approx(20)
    assert summary["max_ms"] == pytest.approx(30)


def test_empty_latency_summary_is_explicitly_unmeasured():
    summary = _latency_summary([])
    assert summary["sample_count"] == 0
    assert summary["mean_ms"] is None
