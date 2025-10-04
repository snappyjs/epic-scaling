# Azure Batch POC

Infrastructure-as-code and helper scripts that demonstrate scaling compute with Azure Service Bus triggering Azure Batch jobs.

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
   JOB_CONTAINER_IMAGE="<terraform output job_container_image>"
   ```

## Build job container image

Terraform provisions an Azure Container Registry for the simple job runner image located in `job/`. After `terraform apply`, gather the outputs `container_registry_name`, `container_registry_login_server`, and `job_container_image`.

1. Authenticate the registry (Azure CLI picks up current credentials):

   ```bash
   az acr login --name <your acr name>
   ```

2. Build and push the image from the repo root:

   ```bash
   docker build -t <job_container_image> job
   docker push <job_container_image>
   ```

(you can now check that your image is available in the ACR)

Terraform defaults the Batch pool to VM size `Standard_D2s_v3` with the container-enabled marketplace image `Canonical/0001-com-ubuntu-server-jammy-container:22_04-lts`. Update `batch_pool_vm_size` or `batch_image` in `terraform/variables.tf` if your workloads need different specs, ensuring the image supports container workloads.

3. Populate `JOB_CONTAINER_IMAGE` in `.env` with the fully qualified image reference so the processor can target the container.

## Send job requests

Use `scripts/send_message.py` to enqueue job tasks. Values default to a 120-second sleep command and auto-generated IDs. This represents your current solution that sends data to the service bus.

```bash
python scripts/send_message.py --count 3
```

Arguments:
- `--job-id`: reuse an existing job identifier
- `--task-id`: specify a task id (auto-generated otherwise)
- `--command`: shell command recorded with the task (printed by the container)
- `--metadata`: JSON string attached to the message
- `--count`: number of identical messages to publish

## Process queue & launch Batch jobs

Run `scripts/process_messages.py` to poll Service Bus, ensure each job exists, and submit tasks to the configured Batch pool.
This represents an azure function to orchestrate the jobs - this should probably replace your current "App Service Calculator"-thingy.

```bash
python scripts/process_messages.py --continuous
```

Key options:
- `--max-messages`: exit after processing the specified number of messages
- `--wait-time`: seconds to wait for new messages before retrying
- `--pull-batch`: maximum messages fetched per request
- `--continuous`: keep polling even when the queue is empty

Ensure `JOB_CONTAINER_IMAGE` is exported (or set in `.env`) so the processor can attach the container when creating tasks.

Each message must contain `job_id` and `task_id`. The send script already formats messages correctly. Tasks now run inside the published container image and emit the received command plus metadata before sleeping for 120 seconds to simulate work.

## Scaling & quotas

- Autoscale targets one dedicated node per pending or running task (up to `var.batch_pool_max_nodes`, default 2). Adjust
  `batch_pool_min_nodes`, `batch_pool_max_nodes`, and `batch_pool_tasks_per_node` in `terraform/variables.tf` to match your workload.
- Low-priority nodes are disabled by default to avoid quota issues. To reintroduce them, set `batch_pool_max_low_priority_nodes`, but
  be aware Azure enforces a separate low-priority core quota per account/region.
- Need a custom autoscale policy? Provide your own formula via `batch_pool_auto_scale_formula`; otherwise, the default formula uses
  the settings above.

## Cleanup

When finished, destroy the infrastructure to avoid costs:

```bash
cd terraform
terraform destroy
```

## Next steps

- Extend message schema to include task resource requirements or payload locations
- Add monitoring/alerting on queue depth and Batch job states
- Update the "/job" to include your "calculation" instead of the sleep timer.
