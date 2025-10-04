# Repository Guidelines

## Project Structure & Module Organization
Terraform lives in `terraform/` and is a single root module orchestrating Service Bus, Storage, Batch, and the new container registry resources. State is local by default; keep `terraform.tfstate*` out of commits and consider a remote backend before collaborating. Python helpers sit in `scripts/`, with `send_message.py` queuing work and `process_messages.py` dispatching Batch tasks. The containerized job runner resides in `job/` (Dockerfile + runtime code). Python dependencies for host scripts stay in `requirements.txt`; environment samples live in `.env.example`.

## Build, Test, and Development Commands
Run `cd terraform && terraform init -upgrade` before planning or applying to pull provider updates. Use `cd terraform && terraform apply` to provision infrastructure; always capture the plan output in your PR. Destroy lab resources with `cd terraform && terraform destroy`. Set up the Python toolchain with `python -m venv .venv` then `source .venv/bin/activate && pip install -r requirements.txt`. Build and push the job runner image with `docker build -t <job_container_image> job` followed by `docker push <job_container_image>` after an `az acr login`. Submit test work items via `python scripts/send_message.py --count 3` and process them with `python scripts/process_messages.py --continuous`.

## Coding Style & Naming Conventions
Follow Python 3.10+ standards: four-space indentation, PEP 8 naming, and type hints for public functions as shown in `scripts/process_messages.py`. Keep CLI flags lowercase with hyphen separators, and prefer f-strings for formatting. Terraform variables use snake_case; resource names should reuse the `var.prefix` to keep Azure assets grouped.

## Testing Guidelines
There is no automated test suite yet; rely on targeted dry-runs. For Terraform changes, run `terraform plan` and attach the diff. When adjusting Python logic, exercise the scripts against a staging queue using `--max-messages` to bound runs, and document manual steps until pytest-based coverage is introduced.

## Commit & Pull Request Guidelines
Commits should stay small, use imperative summaries under 72 characters (e.g., `Add queue polling guard`), and include a short body when explaining context or rollbacks. PRs must describe the change, link any work items, note Terraform plan results, and include screenshots or logs for script behavior whenever possible.

## Security & Configuration Tips
Populate secrets through `.env` or shell exports; never commit filled `.env` files or Terraform state. Treat container registry admin credentials as sensitive—prefer `az acr login` over storing passwords locally. Use `az login` with least-privilege accounts, and rotate connection strings whenever they are shared in non-prod channels.

Batch pools use VM size `Standard_D2s_v3` and the marketplace image `Canonical/0001-com-ubuntu-server-jammy-container:22_04-lts` by default to enable container workloads. If you override `batch_pool_vm_size` or `batch_image`, double-check the image supports the container feature.
