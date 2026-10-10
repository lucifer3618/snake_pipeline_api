output "zone_ids" {
  description = "Resource IDs of the managed DNS zones"
  value       = { for key, zone in azurerm_dns_zone.this : key => zone.id }
}

output "name_servers" {
  description = "Azure DNS name servers for each zone"
  value       = { for key, zone in azurerm_dns_zone.this : key => zone.name_servers }
}

output "custom_domain_ids" {
  description = "Resource IDs of the Container App custom-domain bindings"
  value       = { for key, domain in azurerm_container_app_custom_domain.this : key => domain.id }
}

output "managed_certificate_ids" {
  description = "Resource IDs of the managed certificates"
  value       = { for key, certificate in azurerm_container_app_environment_managed_certificate.this : key => certificate.id }
}
