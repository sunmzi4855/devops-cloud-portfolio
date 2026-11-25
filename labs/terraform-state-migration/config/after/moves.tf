moved {
  from = postgresql_database.legacy[0]
  to   = postgresql_database.workload["orders"]
}

moved {
  from = postgresql_database.legacy[1]
  to   = postgresql_database.workload["audit"]
}
