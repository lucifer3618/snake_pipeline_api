output "resource_group_name" {
  value       = module.resource_group.resource_group_name
  description = "The name of the resource group"
}

output "resource_group_location" {
  value       = module.resource_group.resource_group_location
  description = "The location of the resource group"
}

output "resource_group_id" {
  value       = module.resource_group.resource_group_id
  description = "The ID of the resource group"
}


output "github_actions_client_id" {
  value       = module.github_actions_identity.app_registration_client_id
  description = "The Azure client ID for the GitHub Actions OIDC login"
}

output "github_actions_service_principal_object_id" {
  value       = module.github_actions_identity.service_principal_object_id
  description = "The GitHub Actions service principal object ID"
}

output "container_registry_id" {
  value       = module.container_registry.id
  description = "The Azure Container Registry resource ID"
}

output "container_registry_login_server" {
  value       = module.container_registry.login_server
  description = "The Azure Container Registry login server"
}
