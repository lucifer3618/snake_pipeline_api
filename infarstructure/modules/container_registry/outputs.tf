output "id" {
  description = "The Azure Container Registry resource ID"
  value       = azurerm_container_registry.this.id
}

output "name" {
  description = "The Azure Container Registry name"
  value       = azurerm_container_registry.this.name
}

output "login_server" {
  description = "The Azure Container Registry login server"
  value       = azurerm_container_registry.this.login_server
}
