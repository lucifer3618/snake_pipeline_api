variable "name" {
  description = "The Container App name"
  type        = string
}

variable "container_app_environment_id" {
  description = "The Container Apps environment resource ID"
  type        = string
}

variable "resource_group_name" {
  description = "The resource group containing the Container App"
  type        = string
}

variable "revision_mode" {
  description = "The Container App revision mode"
  type        = string
  default     = "Single"
}

variable "max_inactive_revisions" {
  description = "Maximum number of inactive revisions retained"
  type        = number
  default     = 100
}

variable "workload_profile_name" {
  description = "The environment workload profile used by the app"
  type        = string
  default     = "Consumption"
}

variable "registry_server" {
  description = "The container registry login server"
  type        = string
}

variable "registry_identity" {
  description = "The identity used to pull images from the registry"
  type        = string
  default     = "system-environment"
}

variable "container_name" {
  description = "The application container name"
  type        = string
}

variable "container_image" {
  description = "The initial application container image"
  type        = string
}

variable "container_cpu" {
  description = "CPU cores allocated to the container"
  type        = number
}

variable "container_memory" {
  description = "Memory allocated to the container"
  type        = string
}

variable "environment_variables" {
  description = "Non-secret environment variables used only when initially creating the app"
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "min_replicas" {
  description = "Minimum replica count"
  type        = number
}

variable "max_replicas" {
  description = "Maximum replica count"
  type        = number
}

variable "polling_interval_in_seconds" {
  description = "Scaling polling interval"
  type        = number
}

variable "cooldown_period_in_seconds" {
  description = "Scaling cooldown period"
  type        = number
}

variable "http_scale_rule_name" {
  description = "Name of the HTTP scaling rule"
  type        = string
}

variable "http_concurrent_requests" {
  description = "Concurrent HTTP requests per replica"
  type        = string
}

variable "external_ingress_enabled" {
  description = "Whether ingress is exposed publicly"
  type        = bool
}

variable "allow_insecure_connections" {
  description = "Whether ingress permits insecure HTTP connections"
  type        = bool
}

variable "target_port" {
  description = "Container port targeted by ingress"
  type        = number
}

variable "ingress_transport" {
  description = "Ingress transport mode"
  type        = string
  default     = "auto"
}

variable "tags" {
  description = "Tags assigned to the Container App"
  type        = map(string)
  default     = {}
}
