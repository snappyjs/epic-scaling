#!/usr/bin/env python3
"""Consume Service Bus messages and orchestrate Azure Batch jobs."""

import argparse
import json
import os
import shlex
import sys
import time
from typing import Any, Dict, Iterable, Tuple

from azure.batch import BatchServiceClient
from azure.batch import models as batch_models
from azure.batch.batch_auth import SharedKeyCredentials
from azure.batch.models import BatchErrorException
from azure.servicebus import ServiceBusClient
from dotenv import load_dotenv


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"Environment variable {name} is required")
    return value


def sanitize_batch_credentials(
    account_name: str, account_key: str, account_url: str
) -> Tuple[str, str, str]:
    """Allow either raw values or connection strings copied from the portal."""

    def parse_connection_string(raw: str) -> Dict[str, str]:
        pairs: Dict[str, str] = {}
        for part in raw.split(";"):
            if not part or "=" not in part:
                continue
            key, value = part.split("=", 1)
            pairs[key.strip().lower()] = value.strip()
        return pairs

    lowered_url = account_url.lower()
    if "batchurl=" in lowered_url or "accountkey=" in lowered_url:
        parsed = parse_connection_string(account_url)
        account_url = parsed.get("batchurl", account_url)
        account_key = parsed.get("accountkey", account_key)
        account_name = parsed.get("accountname", account_name)

    lowered_key = account_key.lower()
    if "batchurl=" in lowered_key or "accountkey=" in lowered_key:
        parsed = parse_connection_string(account_key)
        account_url = parsed.get("batchurl", account_url)
        account_key = parsed.get("accountkey", account_key)
        account_name = parsed.get("accountname", account_name)

    if not account_url.lower().startswith("http"):
        raise SystemExit(
            "BATCH_ACCOUNT_URL must be the HTTPS endpoint (e.g. https://<account>.<region>.batch.azure.com)."
        )

    return account_name, account_key, account_url.rstrip("/")


def ensure_job(batch_client: BatchServiceClient, job_id: str, pool_id: str) -> None:
    try:
        batch_client.job.get(job_id)
    except BatchErrorException as exc:
        if exc.error and exc.error.code == "JobNotFound":
            job = batch_models.JobAddParameter(
                id=job_id,
                pool_info=batch_models.PoolInformation(pool_id=pool_id),
            )
            batch_client.job.add(job)
            print(f"Created job '{job_id}' bound to pool '{pool_id}'")
        else:
            raise


def add_task(batch_client: BatchServiceClient, job_id: str, task_id: str, command: str, metadata: Dict[str, Any]) -> None:
    command_line = f"/bin/bash -c {shlex.quote(command)}"
    constraints = batch_models.TaskConstraints(max_task_retry_count=0)
    task = batch_models.TaskAddParameter(
        id=task_id,
        command_line=command_line,
        display_name=metadata.get("display_name", task_id),
        constraints=constraints,
    )

    try:
        batch_client.task.add(job_id=job_id, task=task)
        print(f"Submitted task '{task_id}' to job '{job_id}' -> {command}")
    except BatchErrorException as exc:
        if exc.error and exc.error.code == "TaskExists":
            print(f"Task '{task_id}' already exists in job '{job_id}', skipping")
        else:
            raise


def extract_body(message: Any) -> str:
    body = message.body
    if isinstance(body, bytes):
        return body.decode("utf-8")
    if isinstance(body, str):
        return body
    if isinstance(body, Iterable):
        chunks = [chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk) for chunk in body]
        return "".join(chunks)
    return str(body)


def process_message(batch_client: BatchServiceClient, pool_id: str, message: Any) -> None:
    payload = json.loads(extract_body(message))
    job_id = payload.get("job_id")
    task_id = payload.get("task_id")
    command = payload.get("command", "sleep 120")
    metadata = payload.get("metadata") or {}

    if not job_id or not task_id:
        raise ValueError("Message must contain 'job_id' and 'task_id'")

    ensure_job(batch_client, job_id, pool_id)
    add_task(batch_client, job_id, task_id, command, metadata)


def main() -> None:
    load_dotenv()

    batch_account_name = require_env("BATCH_ACCOUNT_NAME")
    batch_account_key = require_env("BATCH_ACCOUNT_KEY")
    batch_account_url = require_env("BATCH_ACCOUNT_URL")

    batch_account_name, batch_account_key, batch_account_url = sanitize_batch_credentials(
        batch_account_name, batch_account_key, batch_account_url
    )

    connection_string = require_env("SERVICE_BUS_CONNECTION_STRING")
    queue_name = require_env("SERVICE_BUS_QUEUE_NAME")
    batch_pool_id = require_env("BATCH_POOL_ID")

    parser = argparse.ArgumentParser(description="Process messages and submit Batch jobs")
    parser.add_argument(
        "--max-messages",
        dest="max_messages",
        type=int,
        default=None,
        help="Optional cap on number of messages to process before exiting",
    )
    parser.add_argument(
        "--wait-time",
        dest="wait_time",
        type=int,
        default=10,
        help="Receiver wait time in seconds when polling the queue",
    )
    parser.add_argument(
        "--pull-batch",
        dest="pull_batch",
        type=int,
        default=5,
        help="Maximum number of messages to pull per Service Bus request",
    )
    parser.add_argument(
        "--continuous",
        dest="continuous",
        action="store_true",
        help="Keep polling even when the queue is empty",
    )
    args = parser.parse_args()

    credentials = SharedKeyCredentials(batch_account_name, batch_account_key)
    batch_client = BatchServiceClient(credentials, batch_url=batch_account_url)

    processed = 0
    with ServiceBusClient.from_connection_string(connection_string) as sb_client:
        with sb_client.get_queue_receiver(queue_name, max_wait_time=args.wait_time) as receiver:
            while True:
                messages = receiver.receive_messages(max_message_count=args.pull_batch)
                if not messages:
                    if args.continuous:
                        time.sleep(args.wait_time)
                        continue
                    break

                for message in messages:
                    try:
                        process_message(batch_client, batch_pool_id, message)
                        receiver.complete_message(message)
                        processed += 1
                        if args.max_messages and processed >= args.max_messages:
                            print(f"Processed {processed} message(s)")
                            return
                    except Exception as exc:
                        receiver.abandon_message(message)
                        print(f"Failed to process message: {exc!r}")
    print(f"Processed {processed} message(s)")


if __name__ == "__main__":
    main()
