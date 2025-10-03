variable "prefix" {
  description = "Prefix used for naming Azure resources. Should be short and unique."
  type        = string
  default     = "poc"
}

variable "location" {
  description = "Azure region for resource deployment."
  type        = string
  default     = "swedencentral"
}

variable "servicebus_queue_name" {
  description = "Service Bus queue name for job messages."
  type        = string
  default     = "job-requests"
}

variable "servicebus_sku" {
  description = "Service Bus namespace SKU."
  type        = string
  default     = "Standard"
}

variable "batch_pool_id" {
  description = "Identifier for the Azure Batch pool used by jobs."
  type        = string
  default     = "poc-batch-pool"
}

variable "batch_pool_vm_size" {
  description = "Virtual machine size for Batch pool compute nodes."
  type        = string
  default     = "STANDARD_A1_v2"
}

variable "batch_node_agent_sku" {
  description = "Node agent SKU matching the VM image."
  type        = string
  default     = "batch.node.ubuntu 22.04"
}

variable "batch_image" {
  description = "Marketplace image settings for Batch pool nodes."
  type = object({
    publisher = string
    offer     = string
    sku       = string
    version   = string
  })
  default = {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }
}

variable "batch_pool_min_nodes" {
  description = "Minimum number of dedicated nodes to keep in the Batch pool."
  type        = number
  default     = 0
}

variable "batch_pool_max_nodes" {
  description = "Maximum number of dedicated nodes that autoscale can allocate."
  type        = number
  default     = 5
}

variable "batch_pool_max_low_priority_nodes" {
  description = "Maximum number of low-priority nodes that autoscale can allocate (defaults to 0)."
  type        = number
  default     = 0
}

variable "batch_pool_tasks_per_node" {
  description = "Number of tasks each node should run concurrently."
  type        = number
  default     = 1
}

variable "batch_pool_auto_scale_evaluation_interval" {
  description = "Autoscale evaluation interval (ISO 8601 duration)."
  type        = string
  default     = "PT5M"
}

variable "batch_pool_auto_scale_formula" {
  description = "Custom autoscale formula. Leave empty to use the opinionated default."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default     = {}
}
