import {
  to = module.github_actions_identity.azuread_application_registration.this
  id = "/applications/9896dddf-2d54-413f-943a-c8f4de7aa588"
}

import {
  to = module.github_actions_identity.azuread_service_principal.this
  id = "/servicePrincipals/9894ef1d-cad7-4d04-80bb-58fc51265b52"
}

import {
  to = module.github_actions_identity.azuread_application_federated_identity_credential.this
  id = "9896dddf-2d54-413f-943a-c8f4de7aa588/federatedIdentityCredential/ab7bb9c0-1640-4dfe-87fc-2fe6521de699"
}

import {
  to = module.github_actions_identity.azurerm_role_assignment.this
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.Authorization/roleAssignments/1c916e9c-7d84-44ef-ba29-c942db908cf5"
}

import {
  to = module.container_registry.azurerm_container_registry.this
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.ContainerRegistry/registries/snakepipelineacr"
}

import {
  to = module.container_registry.azurerm_role_assignment.this["github_actions_push"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.ContainerRegistry/registries/snakepipelineacr/providers/Microsoft.Authorization/roleAssignments/3185d479-9c2e-4a4f-8489-e2c40cd80de3"
}

import {
  to = module.container_registry.azurerm_role_assignment.this["container_apps_environment_pull"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.ContainerRegistry/registries/snakepipelineacr/providers/Microsoft.Authorization/roleAssignments/fed35e58-01a1-5d1d-a3b1-6c53af96767e"
}

import {
  to = module.container_app.azurerm_container_app.this
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.App/containerApps/snake-pipeline"
}

import {
  to = module.domain_name_zones.azurerm_dns_zone.this["parent"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.Network/dnsZones/horizoninventory.app"
}

import {
  to = module.domain_name_zones.azurerm_dns_zone.this["child"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.Network/dnsZones/snake-pipeline.horizoninventory.app"
}

import {
  to = module.domain_name_zones.azurerm_dns_cname_record.this["backend"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.Network/dnsZones/horizoninventory.app/CNAME/snake-pipeline"
}

import {
  to = module.domain_name_zones.azurerm_dns_txt_record.this["backend_verification"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.Network/dnsZones/horizoninventory.app/TXT/asuid.snake-pipeline"
}

import {
  to = module.domain_name_zones.azurerm_container_app_custom_domain.this["backend"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.App/containerApps/snake-pipeline/customDomainName/snake-pipeline.horizoninventory.app"
}

import {
  to = module.domain_name_zones.azurerm_container_app_environment_managed_certificate.this["parent"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.App/managedEnvironments/snake-pipeline-env/managedCertificates/horizoninventory.app-snake-pi-261008035630"
}

import {
  to = module.domain_name_zones.azurerm_container_app_environment_managed_certificate.this["backend"]
  id = "/subscriptions/0f56e0ee-95ca-451c-b60d-43a7b85beb63/resourceGroups/snake_pipeline_rg/providers/Microsoft.App/managedEnvironments/snake-pipeline-env/managedCertificates/snake-pipeline.horizoninvent-snake-pi-261008041826"
}
