output "storage_account_id" {
  value = azurerm_storage_account.this.id
  description = "The ID of the storage account"
}

output "storage_account_name" {
  value       = azurerm_storage_account.this.name
  description = "The name of the storage account"
}

output "storage_account_primary_connection_string" {
  value       = azurerm_storage_account.this.primary_connection_string
  description = "The primary connection string of the storage account"
}

output "storage_account_primary_blob_endpoint" {
  value       = azurerm_storage_account.this.primary_blob_endpoint
  description = "The primary blob endpoint of the storage account"
}

output "storage_account_primary_blob_host" {
  value       = azurerm_storage_account.this.primary_blob_host
  description = "The primary blob host of the storage account"
}