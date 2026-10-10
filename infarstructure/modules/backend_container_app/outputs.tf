output "id" {
  description = "The Container App resource ID"
  value       = azurerm_container_app.this.id
}

output "name" {
  description = "The Container App name"
  value       = azurerm_container_app.this.name
}

output "fqdn" {
  description = "The default Container App ingress hostname"
  value       = azurerm_container_app.this.ingress[0].fqdn
}

output "custom_domain_verification_id" {
  description = "The verification value required for custom domains"
  value       = azurerm_container_app.this.custom_domain_verification_id
}

output "latest_revision_name" {
  description = "The latest Container App revision name"
  value       = azurerm_container_app.this.latest_revision_name
}
