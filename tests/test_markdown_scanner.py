"""Unit tests for Markdown Scanner."""

from docdrift.markdown_scanner import MarkdownScanner


def test_scan_markdown_tables():
    content = """# API Documentation

### `start_worker()`

Starts an asynchronous worker pool.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `worker_count` | int | Number of worker processes |
| `max_memory` | str | Memory threshold per worker |

```python
start_worker(worker_count=4)
```
"""
    scanner = MarkdownScanner()
    sections = scanner.scan_content(content)

    assert len(sections) >= 1
    worker_sec = [s for s in sections if "start_worker" in s.heading or "start_worker" in s.mentioned_symbols][0]

    assert "worker_count" in worker_sec.documented_params
    assert "max_memory" in worker_sec.documented_params
    assert len(worker_sec.code_blocks) == 1
    assert "start_worker" in worker_sec.mentioned_symbols
