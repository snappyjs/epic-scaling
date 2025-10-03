output "resource_group_name" {
  description = "Name of the created resource group."
  value       = azurerm_resource_group.main.name
}

output "servicebus_namespace_name" {
  description = "Azure Service Bus namespace name."
  value       = azurerm_servicebus_namespace.main.name
}

output "servicebus_queue_name" {
  description = "Azure Service Bus queue name."
  value       = azurerm_servicebus_queue.jobs.name
}

output "servicebus_send_receive_connection_string" {
  description = "Connection string for Service Bus send/receive operations."
  value       = azurerm_servicebus_namespace_authorization_rule.send_receive.primary_connection_string
  sensitive   = true
}

output "batch_account_name" {
  description = "Azure Batch account name."
  value       = azurerm_batch_account.main.name
}

output "batch_account_url" {
  description = "Endpoint URL for the Batch account."
  value       = azurerm_batch_account.main.account_endpoint
}

output "batch_account_primary_access_key" {
  description = "Primary access key for the Batch account."
  value       = azurerm_batch_account.main.primary_access_key
  sensitive   = true
}

output "batch_pool_id" {
  description = "Batch pool identifier."
  value       = azurerm_batch_pool.poc.name
}
