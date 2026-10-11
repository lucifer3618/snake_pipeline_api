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

# ------ Container Registry Variables -------
variable "container_registry_name" {
  description = "The name of the Azure Container Registry"
  type        = string
}

variable "container_registry_sku" {
  description = "The SKU of the Azure Container Registry"
  type        = string
}

# ------ Backend Container App Variables -------
variable "backend_container_app_name" {
  description = "The backend Container App name"
  type        = string
}

variable "backend_container_name" {
  description = "The backend application container name"
  type        = string
}

variable "backend_container_repository" {
  description = "The backend image repository within ACR"
  type        = string
}

variable "backend_container_image_tag" {
  description = "The initial backend image tag; later releases are managed by GitHub Actions"
  type        = string
}

variable "backend_container_cpu" {
  description = "CPU cores assigned to the backend container"
  type        = number
}

variable "backend_container_memory" {
  description = "Memory assigned to the backend container"
  type        = string
}

variable "backend_min_replicas" {
  description = "Minimum backend replica count"
  type        = number
}

variable "backend_max_replicas" {
  description = "Maximum backend replica count"
  type        = number
}

variable "backend_target_port" {
  description = "Backend container ingress port"
  type        = number
}

# ------ Frontend Container App Variables -------
variable "frontend_container_app_name" {
  description = "The frontend Container App name"
  type        = string
}

variable "frontend_container_name" {
  description = "The frontend application container name"
  type        = string
}

variable "frontend_container_repository" {
  description = "The frontend image repository within ACR"
  type        = string
}

variable "frontend_container_image_tag" {
  description = "The initial frontend image tag; later releases are managed by GitHub Actions"
  type        = string
}

variable "frontend_container_cpu" {
  description = "CPU cores assigned to the frontend container"
  type        = number
}

variable "frontend_container_memory" {
  description = "Memory assigned to the frontend container"
  type        = string
}

variable "frontend_min_replicas" {
  description = "Minimum frontend replica count"
  type        = number
}

variable "frontend_max_replicas" {
  description = "Maximum frontend replica count"
  type        = number
}

variable "frontend_target_port" {
  description = "Frontend container ingress port"
  type        = number
}

# ------ DNS and Custom Domain Variables -------
variable "parent_dns_zone_name" {
  description = "The parent Azure DNS zone"
  type        = string
}

variable "child_dns_zone_name" {
  description = "The child Azure DNS zone retained from the live environment"
  type        = string
}

variable "backend_dns_record_name" {
  description = "The backend record name in the parent DNS zone"
  type        = string
}

variable "backend_custom_domain_name" {
  description = "The fully qualified backend custom domain"
  type        = string
}

variable "frontend_dns_record_name" {
  description = "The frontend record name in the parent DNS zone"
  type        = string
}

variable "frontend_custom_domain_name" {
  description = "The fully qualified frontend custom domain"
  type        = string
}

variable "parent_managed_certificate_name" {
  description = "The existing managed certificate name for the parent domain"
  type        = string
}

variable "backend_managed_certificate_name" {
  description = "The existing managed certificate name for the backend custom domain"
  type        = string
}

variable "frontend_managed_certificate_name" {
  description = "The managed certificate name for the frontend custom domain"
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

# ------ Storage Account Variables -------
variable "storage_account_name" {
  description = "The name of the storage account"
  type        = string
}

variable "storage_account_tier" {
  description = "The tier of the storage account"
  type        = string
}

variable "storage_account_replication_type" {
  description = "The replication type of the storage account"
  type        = string
}

variable "storage_containers" {
  description = "A map of storage containers to create"
  type = map(object({
    name        = string
    access_type = string
  }))
  default = {}
}
