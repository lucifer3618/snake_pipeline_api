# ------- Resource Group Variables -------
variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "location" {
  description = "The location of the resource group"
  type        = string
}


# ------ Log Analytics Workspace Variables -------
variable "log_analytics_workspace_name" {
  description = "The name of the Log Analytics workspace"
  type        = string
}

variable "log_analytics_workspace_sku" {
  description = "The SKU of the Log Analytics workspace"
  type        = string
}

variable "log_analytics_workspace_retention_in_days" {
  description = "The retention period of the Log Analytics workspace in days"
  type        = number
}

variable "tags" {
  description = "Tags to be applied to the Log Analytics workspace"
  type        = map(string)
}

# ------ Container Apps Environment Variables -------
variable "container_apps_environment_name" {
  description = "The name of the container apps environment"
  type        = string
}

variable "logs_destination" {
  description = "The destination of the logs"
  type        = string
}

# ------ Identity Variables -------
variable "app_registration_name" {
  description = "The name of the app registration"
  type        = string
}

variable "federated_identity_name" {
  description = "The name of the federated identity"
  type        = string
}

variable "federated_identity_audiences" {
  description = "The audiences of the federated identity"
  type        = list(string)
}

variable "federated_identity_issuer" {
  description = "The issuer of the federated identity"
  type        = string
}

variable "federated_identity_subject" {
  description = "The subject of the federated identity"
  type        = string
}