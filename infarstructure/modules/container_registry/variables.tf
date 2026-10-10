variable "name" {
  description = "The Azure Container Registry name"
  type        = string
}

variable "resource_group_name" {
  description = "The resource group containing the registry"
  type        = string
}

variable "location" {
  description = "The Azure region for the registry"
  type        = string
}

variable "sku" {
  description = "The Azure Container Registry SKU"
  type        = string
  default     = "Standard"
}

variable "admin_enabled" {
  description = "Whether the registry admin account is enabled"
  type        = bool
  default     = false
}

variable "anonymous_pull_enabled" {
  description = "Whether anonymous image pulls are enabled"
  type        = bool
  default     = false
}

variable "azuread_authentication_as_arm_policy_enabled" {
  description = "Whether Entra authentication is enabled for ARM policy operations"
  type        = bool
  default     = true
}

variable "data_endpoint_enabled" {
  description = "Whether dedicated data endpoints are enabled"
  type        = bool
  default     = false
}

variable "export_policy_enabled" {
  description = "Whether image export is enabled"
  type        = bool
  default     = true
}

variable "network_rule_bypass_option" {
  description = "The network rule bypass option"
  type        = string
  default     = "AzureServices"
}

variable "public_network_access_enabled" {
  description = "Whether public network access is enabled"
  type        = bool
  default     = true
}

variable "quarantine_policy_enabled" {
  description = "Whether image quarantine is enabled"
  type        = bool
  default     = false
}

variable "role_assignment_mode" {
  description = "The registry role assignment mode"
  type        = string
  default     = "LegacyRegistryPermissions"
}

variable "zone_redundancy_enabled" {
  description = "Whether zone redundancy is enabled"
  type        = bool
  default     = false
}

variable "role_assignments" {
  description = "Registry-scoped role assignments keyed by a stable logical name"
  type = map(object({
    principal_id         = string
    role_definition_name = string
    principal_type       = optional(string, "ServicePrincipal")
  }))
  default = {}
}

variable "tags" {
  description = "Tags assigned to the registry"
  type        = map(string)
  default     = {}
}
