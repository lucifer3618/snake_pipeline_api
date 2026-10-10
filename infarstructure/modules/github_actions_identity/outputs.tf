output "app_registration_id" {
  value = azuread_application_registration.this.id
  description = "The ID of the Azure application registration"
}

output "app_registration_name" {
  value = azuread_application_registration.this.display_name
  description = "The name of the Azure application registration"
}

output "app_registration_object_id" {
  value = azuread_application_registration.this.object_id
  description = "The object ID of the Azure application registration"
}

output "federated_identity_credential_name" {
  value = azuread_application_federated_identity_credential.this.display_name
  description = "The name of the federated identity credential"
}

output "federated_identity_credential_id" {
  value = azuread_application_federated_identity_credential.this.id
  description = "The ID of the federated identity credential"
}