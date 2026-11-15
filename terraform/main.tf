terraform {
  required_version = ">= 1.5.0"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

# A free, local-only example of declarative infrastructure provisioning.
# No cloud account, credentials, or costs are required.
resource "local_file" "deployment_manifest" {
  filename = "${path.module}/deployment-info.json"
  content = jsonencode({
    service     = var.service_name
    environment = var.environment
    port        = 8080
  })
}
