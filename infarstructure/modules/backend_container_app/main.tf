resource "azurerm_container_app" "this" {
  name                         = var.name
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = var.revision_mode
  max_inactive_revisions       = var.max_inactive_revisions
  workload_profile_name        = var.workload_profile_name

  registry {
    server   = var.registry_server
    identity = var.registry_identity
  }

  template {
    min_replicas                = var.min_replicas
    max_replicas                = var.max_replicas
    polling_interval_in_seconds = var.polling_interval_in_seconds
    cooldown_period_in_seconds  = var.cooldown_period_in_seconds

    container {
      name   = var.container_name
      image  = var.container_image
      cpu    = var.container_cpu
      memory = var.container_memory

      dynamic "env" {
        for_each = var.environment_variables
        content {
          name  = env.key
          value = env.value
        }
      }
    }

    http_scale_rule {
      name                = var.http_scale_rule_name
      concurrent_requests = var.http_concurrent_requests
    }
  }

  ingress {
    external_enabled           = var.external_ingress_enabled
    allow_insecure_connections = var.allow_insecure_connections
    target_port                = var.target_port
    transport                  = var.ingress_transport

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [
      template[0].container[0].image,
      template[0].container[0].env,
    ]
  }
}
