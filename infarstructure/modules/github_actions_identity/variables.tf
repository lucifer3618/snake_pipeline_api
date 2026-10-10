variable "app_registration_name" {
  type = string
  description = "Azure application registration name"
}

variable "federated_identity_name" {
  type = string
  description = "Federated identity name"
}

variable "federated_identity_audiences" {
  type = list(string)
  description = "List of audiences for the federated identity"
}

variable "federated_identity_issuer" {
  type = string
  description = "Issuer for the federated identity"
}

variable "federated_identity_subject" {
  type = string
  description = "Subject for the federated identity"
}

variable "resource_group_id" {
  type        = string
  description = "Resource group scope where GitHub Actions receives Contributor access"
}
