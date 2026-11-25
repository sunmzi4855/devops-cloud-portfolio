terraform {
  required_version = "= 1.12.2"

  required_providers {
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "= 1.25.0"
    }
  }
}

variable "pg_port" {
  type = number
}

provider "postgresql" {
  host     = "127.0.0.1"
  port     = var.pg_port
  database = "postgres"
  username = "postgres"
  sslmode  = "disable"
}
