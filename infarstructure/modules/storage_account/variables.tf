variable "storage_account_name" {
  description = "The name of the storage account."
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create the storage account."
  type        = string
}

variable "location" {
  description = "The Azure region in which to create the storage account."
  type        = string
}

variable "storage_account_tier" {
  description = "The tier of the storage account."
  type        = string
}

variable "storage_account_replication_type" {
  description = "The replication type of the storage account."
  type        = string
}

variable "storage_containers" {
  description = "A map of storage containers to create."
  type = map(object({
    name        = string
    access_type = string
  }))
  default = {}
}

variable "tags" {
  description = "A map of tags to assign to the storage account."
  type        = map(string)
  default     = {}
}