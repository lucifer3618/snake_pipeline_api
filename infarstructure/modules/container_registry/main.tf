resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku

  admin_enabled                                = var.admin_enabled
  anonymous_pull_enabled                       = var.anonymous_pull_enabled
  azuread_authentication_as_arm_policy_enabled = var.azuread_authentication_as_arm_policy_enabled
  data_endpoint_enabled                        = var.data_endpoint_enabled
  export_policy_enabled                        = var.export_policy_enabled
  network_rule_bypass_option                   = var.network_rule_bypass_option
  public_network_access_enabled                = var.public_network_access_enabled
  quarantine_policy_enabled                    = var.quarantine_policy_enabled
  role_assignment_mode                         = var.role_assignment_mode
  zone_redundancy_enabled                      = var.zone_redundancy_enabled

  tags = var.tags
}

resource "azurerm_role_assignment" "this" {
  for_each = var.role_assignments

  scope                = replace(azurerm_container_registry.this.id, "/resourceGroups", "/resourcegroups")
  role_definition_name = each.value.role_definition_name
  principal_id         = each.value.principal_id
  principal_type       = each.value.principal_type
}
