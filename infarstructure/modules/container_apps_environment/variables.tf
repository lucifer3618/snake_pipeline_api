variable "container_apps_environment_name" {
  description = "The name of the container apps environment"
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "location" {
  description = "The location of the resource group"
  type        = string
}

variable "logs_destination" {
  description = "The destination of the logs"
  type        = string
}

variable "logs_analytics_workspace_id" {
  description = "The ID of the Log Analytics workspace"
  type        = string
}

variable "tags" {
  description = "Tags to be applied to the container apps environment"
  type        = map(string)
}
