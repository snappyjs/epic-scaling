#!/usr/bin/env python3
"""Azure Batch container entrypoint for the POC job runner."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from rich.console import Console
from rich.json import JSON

console = Console()


def load_metadata(raw: str | None) -> Dict[str, Any]:
    """Parse metadata JSON passed from the orchestrator, tolerating bad input."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw, "_warning": "Metadata was not valid JSON"}


def read_sleep_seconds() -> int:
    raw_value = os.getenv("TASK_SLEEP_SECONDS", "120")
    try:
        return max(0, int(raw_value))
    except ValueError:
        console.print(f"[yellow]Invalid TASK_SLEEP_SECONDS '{raw_value}', falling back to 120")
        return 120


def main() -> None:
    job_id = os.getenv("TASK_JOB_ID", "")
    task_id = os.getenv("TASK_ID", "")
    command = os.getenv("TASK_COMMAND", "")
    metadata = load_metadata(os.getenv("TASK_METADATA"))
    attempt = os.getenv("TASK_ATTEMPT", "1")

    console.rule("Azure Batch Job Context")
    console.print(f"[bold]Job ID:[/] {job_id or '<unknown>'}")
    console.print(f"[bold]Task ID:[/] {task_id or '<unknown>'}")
    console.print(f"[bold]Attempt:[/] {attempt}")
    if command:
        console.print(f"[bold]Command:[/] {command}")

    if metadata:
        console.print("[bold]Metadata:[/]")
        console.print(JSON.from_data(metadata))
    else:
        console.print("[bold]Metadata:[/] <none provided>")

    sleep_seconds = read_sleep_seconds()
    console.print(f"[green]Simulating work for {sleep_seconds} second(s)...")
    time.sleep(sleep_seconds)
    console.print("[green]Job complete.")


if __name__ == "__main__":
    main()
