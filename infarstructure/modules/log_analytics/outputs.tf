output "log_analytics_workspace_name" {
  value       = azurerm_log_analytics_workspace.this.name
  description = "The name of the Log Analytics workspace"
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.this.id
  description = "The ID of the Log Analytics workspace"
}