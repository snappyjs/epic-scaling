# Azure Batch POC

Infrastructure-as-code and helper scripts that demonstrate scaling compute with Azure Service Bus triggering Azure Batch jobs.

## Prerequisites

- Terraform `>= 1.7.5` (see https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
- AzureRM provider `~> 3.110` (downloaded automatically by Terraform)
- Azure subscription access with rights to create resource groups, Service Bus, Storage, and Batch resources
- Python `>= 3.10`
- Optional: Azure CLI for authenticating (`az login`)

## Deploy infrastructure

1. Authenticate Terraform (e.g., using `az login` and environment variables for the AzureRM provider).
2. Initialize and apply:

   ```bash
   cd terraform
   terraform init -upgrade
   terraform apply
   ```

## Python environment

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy the environment template and populate it with the Terraform outputs gathered above:

   ```bash
   cp .env.example .env
   ```

   Update `.env` with the values returned by Terraform:

   ```dotenv
   SERVICE_BUS_CONNECTION_STRING="<from terraform output>"
   SERVICE_BUS_QUEUE_NAME="<from terraform output>"
   BATCH_ACCOUNT_NAME="<from terraform output>"
   BATCH_ACCOUNT_KEY="<from terraform output>"
   BATCH_ACCOUNT_URL="<from terraform output>"
   BATCH_POOL_ID="<from terraform output>"
   ```

   The worker tolerates either the raw key/URL or the full Batch connection string copied from the Azure Portal—the script will extract the pieces it needs. Values exported in the shell still override anything in `.env`.

## Send job requests

Use `scripts/send_message.py` to enqueue job tasks. Values default to a 120-second sleep command and auto-generated IDs.

```bash
python scripts/send_message.py --count 3
```

Arguments:
- `--job-id`: reuse an existing job identifier
- `--task-id`: specify a task id (auto-generated otherwise)
- `--command`: shell command to execute inside the Batch node
- `--metadata`: JSON string attached to the message
- `--count`: number of identical messages to publish

## Process queue & launch Batch jobs

Run `scripts/process_messages.py` to poll Service Bus, ensure each job exists, and submit tasks to the configured Batch pool.

```bash
python scripts/process_messages.py --continuous
```

Key options:
- `--max-messages`: exit after processing the specified number of messages
- `--wait-time`: seconds to wait for new messages before retrying
- `--pull-batch`: maximum messages fetched per request
- `--continuous`: keep polling even when the queue is empty

Each message must contain `job_id` and `task_id`. The send script already formats messages correctly. The task command defaults to `sleep 120`, demonstrating how Batch can scale out simple workloads.

## Scaling & quotas

- Autoscale targets one dedicated node per pending or running task (up to `var.batch_pool_max_nodes`, default 5). Adjust
  `batch_pool_min_nodes`, `batch_pool_max_nodes`, and `batch_pool_tasks_per_node` in `terraform/variables.tf` to match your workload.
- Low-priority nodes are disabled by default to avoid quota issues. To reintroduce them, set `batch_pool_max_low_priority_nodes`, but
  be aware Azure enforces a separate low-priority core quota per account/region.
- If you hit `AccountLowPriorityCoreQuotaReached` or similar errors, request a quota increase in the Azure Portal under
  *Batch accounts → Quotas* (or switch to dedicated cores) before reapplying Terraform.
- Need a custom autoscale policy? Provide your own formula via `batch_pool_auto_scale_formula`; otherwise, the default formula uses
  the settings above.

## Cleanup

When finished, destroy the infrastructure to avoid costs:

```bash
cd terraform
terraform destroy
```

## Next steps

- Integrate with custom Batch images or containers for real workloads
- Extend message schema to include task resource requirements or payload locations
- Add monitoring/alerting on queue depth and Batch job states
