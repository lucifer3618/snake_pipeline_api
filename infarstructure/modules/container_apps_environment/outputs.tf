output "container_apps_environment_d" {
  value       = azurerm_container_app_environment.this.id
  description = "The ID of the container apps environment"
}

output "container_apps_environment_id" {
  value       = azurerm_container_app_environment.this.id
  description = "The ID of the container apps environment"
}

output "principal_id" {
  value       = azurerm_container_app_environment.this.identity[0].principal_id
  description = "The object ID of the environment system-assigned identity"
}

output "container_apps_environment_name" {
  value       = azurerm_container_app_environment.this.name
  description = "The name of the container apps environment"
}