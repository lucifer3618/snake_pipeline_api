resource "azuread_application_registration" "this" {
  display_name = var.app_registration_name
  description = "Application registration for GitHub Actions identity"
}

resource "azuread_application_federated_identity_credential" "this" {
  application_id = azuread_application_registration.this.object_id
  display_name   = var.federated_identity_name
  description    = "OIDC credential for GitHub Actions release environment"
  audiences      = var.federated_identity_audiences
  issuer         = var.federated_identity_issuer
  subject        = var.federated_identity_subject
}