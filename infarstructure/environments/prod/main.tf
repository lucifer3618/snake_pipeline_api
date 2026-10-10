module "resource_group" {
  source              = "../../modules/resource_group"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

module "log_analytics" {
  source                                    = "../../modules/log_analytics"
  log_analytics_workspace_name              = var.log_analytics_workspace_name
  location                                  = var.location
  resource_group_name                       = module.resource_group.resource_group_name
  log_analytics_workspace_sku               = var.log_analytics_workspace_sku
  log_analytics_workspace_retention_in_days = var.log_analytics_workspace_retention_in_days

  tags = var.tags
}

module "container_apps_environment" {
  source                          = "../../modules/container_apps_environment"
  container_apps_environment_name = var.container_apps_environment_name
  resource_group_name             = module.resource_group.resource_group_name
  location                        = var.location
  logs_destination                = var.logs_destination
  logs_analytics_workspace_id     = module.log_analytics.log_analytics_workspace_id

  tags = var.tags
}

module "github_actions_identity" {
  source                       = "../../modules/github_actions_identity"
  resource_group_id            = module.resource_group.resource_group_id
  app_registration_name        = var.app_registration_name
  federated_identity_name      = var.federated_identity_name
  federated_identity_audiences = var.federated_identity_audiences
  federated_identity_issuer    = var.federated_identity_issuer
  federated_identity_subject   = var.federated_identity_subject
}

module "container_registry" {
  source = "../../modules/container_registry"

  name                = var.container_registry_name
  resource_group_name = module.resource_group.resource_group_name
  location            = var.location
  sku                 = var.container_registry_sku

  role_assignments = {
    github_actions_push = {
      principal_id         = module.github_actions_identity.service_principal_object_id
      role_definition_name = "AcrPush"
    }
    container_apps_environment_pull = {
      principal_id         = module.container_apps_environment.principal_id
      role_definition_name = "AcrPull"
    }
  }

  tags = var.tags
}
