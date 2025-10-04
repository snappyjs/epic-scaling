resource "random_string" "resource_suffix" {
  length  = 6
  upper   = false
  lower   = true
  numeric = true
  special = false
}

locals {
  sanitized_prefix          = join("", regexall("[a-z0-9]", lower(var.prefix)))
  suffix                    = random_string.resource_suffix.result
  resource_group_name       = "${var.prefix}-rg-${local.suffix}"
  servicebus_namespace_name = substr("${local.sanitized_prefix}-sb-${local.suffix}", 0, 50)
  storage_account_name      = substr("${local.sanitized_prefix}${local.suffix}", 0, 24)
  batch_account_name        = substr("${local.sanitized_prefix}batch${local.suffix}", 0, 24)
  container_registry_name   = substr("${local.sanitized_prefix}acr${local.suffix}", 0, 50)

  default_batch_pool_auto_scale_formula = <<-EOT
    startingNumberOfVMs = ${var.batch_pool_min_nodes};
    maxDedicated = ${var.batch_pool_max_nodes};
    maxLowPriority = ${var.batch_pool_max_low_priority_nodes};
    tasksPerNode = max(1, ${var.batch_pool_tasks_per_node});
    $pendingTasks = max(0, $PendingTasks.GetSample(1));
    $runningTasks = max(0, $RunningTasks.GetSample(1));
    $targetTasks = max($pendingTasks, $runningTasks);
    targetDedicated = max(startingNumberOfVMs, min(maxDedicated, ceil($targetTasks / tasksPerNode)));
    $TargetDedicatedNodes = targetDedicated;
    $TargetLowPriorityNodes = min(maxLowPriority, max(0, ceil(($targetTasks - targetDedicated * tasksPerNode) / tasksPerNode)));
  EOT

  batch_pool_auto_scale_formula = trimspace(var.batch_pool_auto_scale_formula) != "" ? var.batch_pool_auto_scale_formula : local.default_batch_pool_auto_scale_formula
}

resource "azurerm_resource_group" "main" {
  name     = local.resource_group_name
  location = var.location
}

resource "azurerm_storage_account" "batch" {
  name                     = local.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_container_registry" "main" {
  name                = local.container_registry_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.container_registry_sku
  admin_enabled       = true

  tags = var.tags
}

locals {
  job_container_image = "${azurerm_container_registry.main.login_server}/${var.job_container_image_repository}:${var.job_container_image_tag}"
}

resource "azurerm_servicebus_namespace" "main" {
  name                = local.servicebus_namespace_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.servicebus_sku
  minimum_tls_version = "1.2"

  tags = var.tags
}

resource "azurerm_servicebus_queue" "jobs" {
  name                         = var.servicebus_queue_name
  namespace_id                 = azurerm_servicebus_namespace.main.id
  enable_partitioning          = true
  requires_duplicate_detection = false
  max_delivery_count           = 10
}

resource "azurerm_servicebus_namespace_authorization_rule" "send_receive" {
  name         = "send-receive"
  namespace_id = azurerm_servicebus_namespace.main.id
  listen       = true
  send         = true
  manage       = false
}

resource "azurerm_batch_account" "main" {
  name                                = local.batch_account_name
  resource_group_name                 = azurerm_resource_group.main.name
  location                            = azurerm_resource_group.main.location
  pool_allocation_mode                = "BatchService"
  storage_account_id                  = azurerm_storage_account.batch.id
  storage_account_authentication_mode = "StorageKeys"

  tags = var.tags
}

resource "azurerm_batch_pool" "poc" {
  name                = var.batch_pool_id
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_batch_account.main.name
  display_name        = "POC Batch Pool"

  vm_size            = var.batch_pool_vm_size
  node_agent_sku_id  = var.batch_node_agent_sku
  max_tasks_per_node = var.batch_pool_tasks_per_node

  storage_image_reference {
    publisher = var.batch_image.publisher
    offer     = var.batch_image.offer
    sku       = var.batch_image.sku
    version   = var.batch_image.version
  }

  container_configuration {
    type = "DockerCompatible"
    container_registries {
      registry_server = azurerm_container_registry.main.login_server
      user_name       = azurerm_container_registry.main.admin_username
      password        = azurerm_container_registry.main.admin_password
    }
  }

  auto_scale {
    evaluation_interval = var.batch_pool_auto_scale_evaluation_interval
    formula             = local.batch_pool_auto_scale_formula
  }

  start_task {
    command_line     = "/bin/bash -c 'echo Batch pool ready'"
    wait_for_success = true
    user_identity {
      auto_user {
        scope           = "Pool"
        elevation_level = "Admin"
      }
    }
  }
}
