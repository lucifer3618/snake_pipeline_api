resource "azurerm_container_app_environment" "this" {
  name = var.container_apps_environment_name
  resource_group_name = var.resource_group_name
  location = var.location
  logs_destination = var.logs_destination
  log_analytics_workspace_id = var.logs_analytics_workspace_id

  # Common tags
  tags = var.tags
}