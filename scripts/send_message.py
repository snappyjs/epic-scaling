#!/usr/bin/env python3
"""Send job requests to the Azure Service Bus queue."""

import argparse
import json
import os
import sys
import uuid
from typing import Any, Dict

from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv


def build_message(job_id: str, task_id: str, command: str, metadata: Dict[str, Any]) -> ServiceBusMessage:
    payload = {
        "job_id": job_id,
        "task_id": task_id,
        "command": command,
        "metadata": metadata,
    }
    return ServiceBusMessage(json.dumps(payload))


def main() -> None:
    load_dotenv()

    connection_string = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    queue_name = os.getenv("SERVICE_BUS_QUEUE_NAME")

    if not connection_string or not queue_name:
        sys.exit("SERVICE_BUS_CONNECTION_STRING and SERVICE_BUS_QUEUE_NAME environment variables are required")

    parser = argparse.ArgumentParser(description="Send a Batch job request message")
    parser.add_argument("--job-id", dest="job_id", help="Job identifier to target. Defaults to a generated value.")
    parser.add_argument("--task-id", dest="task_id", help="Task identifier to use. Defaults to a generated value.")
    parser.add_argument(
        "--command",
        dest="command",
        default="sleep 120",
        help="Command executed by the Batch task (default: sleep 120)",
    )
    parser.add_argument(
        "--metadata",
        dest="metadata",
        default="{}",
        help="Optional JSON metadata attached to the message",
    )
    parser.add_argument(
        "--count",
        dest="count",
        type=int,
        default=1,
        help="Number of identical messages to send (default: 1)",
    )

    args = parser.parse_args()

    try:
        metadata = json.loads(args.metadata)
        if not isinstance(metadata, dict):
            raise ValueError("Metadata JSON must decode to an object")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid metadata JSON: {exc}") from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    job_id = args.job_id or f"job-{uuid.uuid4().hex[:8]}"
    command = args.command

    with ServiceBusClient.from_connection_string(connection_string) as client:
        sender = client.get_queue_sender(queue_name)
        with sender:
            for index in range(args.count):
                task_id = args.task_id or f"task-{uuid.uuid4().hex[:8]}-{index}"
                message = build_message(job_id, task_id, command, metadata)
                sender.send_messages(message)
                print(f"Queued message for job '{job_id}' task '{task_id}'")


if __name__ == "__main__":
    main()
