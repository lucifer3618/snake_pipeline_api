output "container_apps_environment_d" {
  value       = azurerm_container_app_environment.this.id
  description = "The ID of the container apps environment"
}

output "container_apps_environment_name" {
  value       = azurerm_container_app_environment.this.name
  description = "The name of the container apps environment"
}