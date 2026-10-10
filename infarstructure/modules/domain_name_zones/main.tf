resource "azurerm_dns_zone" "this" {
  for_each = var.zones

  name                = each.value.name
  resource_group_name = var.resource_group_name
  tags                = each.value.tags
}

resource "azurerm_dns_cname_record" "this" {
  for_each = var.cname_records

  name                = each.value.name
  zone_name           = azurerm_dns_zone.this[each.value.zone_key].name
  resource_group_name = var.resource_group_name
  ttl                 = each.value.ttl
  record              = each.value.record
  tags                = each.value.tags
}

resource "azurerm_dns_txt_record" "this" {
  for_each = var.txt_records

  name                = each.value.name
  zone_name           = azurerm_dns_zone.this[each.value.zone_key].name
  resource_group_name = var.resource_group_name
  ttl                 = each.value.ttl
  tags                = each.value.tags

  dynamic "record" {
    for_each = toset(each.value.values)
    content {
      value = record.value
    }
  }

  lifecycle {
    # The Container App verification ID is sensitive/computed, which otherwise
    # produces a false in-place update while importing an identical live value.
    ignore_changes = [record]
  }
}

resource "azurerm_container_app_custom_domain" "this" {
  for_each = var.custom_domains

  name             = each.value.name
  container_app_id = var.container_app_id

  depends_on = [
    azurerm_dns_cname_record.this,
    azurerm_dns_txt_record.this,
  ]

  lifecycle {
    # Azure asynchronously attaches and renews its managed certificate.
    ignore_changes = [
      certificate_binding_type,
      container_app_environment_certificate_id,
    ]
  }
}

resource "azurerm_container_app_environment_managed_certificate" "this" {
  for_each = var.managed_certificates

  name                         = each.value.name
  container_app_environment_id = var.container_app_environment_id
  subject_name                 = each.value.subject_name
  domain_control_validation    = each.value.domain_control_validation
  tags                         = each.value.tags

  depends_on = [azurerm_container_app_custom_domain.this]
}
