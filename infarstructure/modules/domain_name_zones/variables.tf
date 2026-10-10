variable "resource_group_name" {
  description = "The resource group containing the DNS zones"
  type        = string
}

variable "container_app_id" {
  description = "The Container App resource ID"
  type        = string
}

variable "container_app_environment_id" {
  description = "The Container Apps environment resource ID"
  type        = string
}

variable "zones" {
  description = "Public DNS zones keyed by a stable logical name"
  type = map(object({
    name = string
    tags = optional(map(string), {})
  }))
}

variable "cname_records" {
  description = "CNAME records keyed by a stable logical name"
  type = map(object({
    zone_key = string
    name     = string
    record   = string
    ttl      = number
    tags     = optional(map(string), {})
  }))
  default = {}
}

variable "txt_records" {
  description = "TXT records keyed by a stable logical name"
  type = map(object({
    zone_key = string
    name     = string
    values   = list(string)
    ttl      = number
    tags     = optional(map(string), {})
  }))
  default = {}
}

variable "custom_domains" {
  description = "Container App custom-domain bindings keyed by a stable logical name"
  type = map(object({
    name = string
  }))
  default = {}
}

variable "managed_certificates" {
  description = "Container Apps environment managed certificates keyed by a stable logical name"
  type = map(object({
    name                      = string
    subject_name              = string
    domain_control_validation = string
    tags                      = optional(map(string), {})
  }))
  default = {}
}
