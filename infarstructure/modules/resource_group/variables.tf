variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "location" {
  description = "The location of the resource group"
  type        = string
}

variable tags {
  description = "Tags to be applied to the resource group"
  type        = map(string)
}