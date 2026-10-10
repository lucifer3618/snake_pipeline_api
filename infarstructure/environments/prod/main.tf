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

module "backend_container_app" {
  source = "../../modules/backend_container_app"

  name                         = var.backend_container_app_name
  container_app_environment_id = module.container_apps_environment.container_apps_environment_id
  resource_group_name          = module.resource_group.resource_group_name

  registry_server   = module.container_registry.login_server
  registry_identity = "system-environment"

  container_name   = var.backend_container_name
  container_image  = "${module.container_registry.login_server}/${var.backend_container_repository}:${var.backend_container_image_tag}"
  container_cpu    = var.backend_container_cpu
  container_memory = var.backend_container_memory

  min_replicas                = var.backend_min_replicas
  max_replicas                = var.backend_max_replicas
  polling_interval_in_seconds = 30
  cooldown_period_in_seconds  = 300
  http_scale_rule_name        = "http-scaler"
  http_concurrent_requests    = "10"

  external_ingress_enabled   = true
  allow_insecure_connections = false
  target_port                = var.backend_target_port
  ingress_transport          = "auto"

  depends_on = [module.container_registry]
}

module "domain_name_zones" {
  source = "../../modules/domain_name_zones"

  resource_group_name          = module.resource_group.resource_group_name
  container_app_id             = module.backend_container_app.id
  container_app_environment_id = module.container_apps_environment.container_apps_environment_id

  zones = {
    parent = {
      name = var.parent_dns_zone_name
    }
    child = {
      name = var.child_dns_zone_name
    }
  }

  cname_records = {
    backend = {
      zone_key = "parent"
      name     = var.backend_dns_record_name
      record   = module.backend_container_app.fqdn
      ttl      = 3600
    }
  }

  txt_records = {
    backend_verification = {
      zone_key = "parent"
      name     = "asuid.${var.backend_dns_record_name}"
      values   = [module.backend_container_app.custom_domain_verification_id]
      ttl      = 3600
    }
  }

  custom_domains = {
    backend = {
      name = var.backend_custom_domain_name
    }
  }

  managed_certificates = {
    parent = {
      name                      = var.parent_managed_certificate_name
      subject_name              = var.parent_dns_zone_name
      domain_control_validation = "HTTP"
    }
    backend = {
      name                      = var.backend_managed_certificate_name
      subject_name              = var.backend_custom_domain_name
      domain_control_validation = "CNAME"
    }
  }
}
