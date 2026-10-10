module "resource_group" {
  source = "../../modules/resource_group"
  resource_group_name = var.resource_group_name
  location = var.location

  tags = var.tags
}

module "log_analytics" {
  source = "../../modules/log_analytics"
  log_analytics_workspace_name = var.log_analytics_workspace_name
  location = var.location
  resource_group_name = module.resource_group.resource_group_name
  log_analytics_workspace_sku = var.log_analytics_workspace_sku
  log_analytics_workspace_retention_in_days = var.log_analytics_workspace_retention_in_days

  tags = var.tags
}

module "container_apps_environment" {
  source = "../../modules/container_apps_environment"
  container_apps_environment_name = var.container_apps_environment_name
  resource_group_name = module.resource_group.resource_group_name
  location = var.location
  logs_destination = var.logs_destination
  logs_analytics_workspace_id = module.log_analytics.log_analytics_workspace_id

  tags = var.tags
}