resource "azuread_application_registration" "this" {
  display_name = var.app_registration_name

  lifecycle {
    ignore_changes = [requested_access_token_version]
  }
}

resource "azuread_service_principal" "this" {
  client_id = azuread_application_registration.this.client_id
}

resource "azuread_application_federated_identity_credential" "this" {
  application_id = azuread_application_registration.this.id
  display_name = var.federated_identity_name
  audiences = var.federated_identity_audiences
  issuer = var.federated_identity_issuer
  subject = var.federated_identity_subject
}

resource "azurerm_role_assignment" "this" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.this.object_id
  principal_type       = "ServicePrincipal"
}
