resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location

  # Common tags
  tags = var.tags
}