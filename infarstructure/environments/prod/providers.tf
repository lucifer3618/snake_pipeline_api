terraform {
  backend "azurerm" {
    resource_group_name  = "snake_pipeline_rg"
    storage_account_name = "snakepipeline"
    container_name       = "tfstate"
    key                  = "demo.terraform.tfstate"
    use_azuread_auth     = true
    use_cli              = true
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {}
