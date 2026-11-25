locals {
  database_names = ["orders", "audit"]
}

resource "postgresql_database" "legacy" {
  count = length(local.database_names)
  name  = local.database_names[count.index]
}
