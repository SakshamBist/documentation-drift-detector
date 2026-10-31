"""Unit tests for the Historical Benchmark Suite."""

from benchmarks.historical_benchmark import run_benchmark


def test_historical_benchmark_metrics():
    """Verify that DocDrift achieves 100% recall and 0% false alarms across benchmark suite."""
    metrics = run_benchmark()
    assert metrics["recall"] == 100.0, f"Expected 100% recall, got {metrics['recall']}%"
    assert metrics["false_alarm_rate"] == 0.0, f"Expected 0% false alarms, got {metrics['false_alarm_rate']}%"
    assert metrics["precision"] == 100.0, f"Expected 100% precision, got {metrics['precision']}%"
    assert metrics["tp"] == 4
    assert metrics["tn"] == 4
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
