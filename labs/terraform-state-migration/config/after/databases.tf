variable "orders_connection_limit" {
  type    = number
  default = -1
}

resource "postgresql_database" "workload" {
  for_each         = toset(["audit", "orders"])
  name             = each.key
  connection_limit = each.key == "orders" ? var.orders_connection_limit : -1
}
