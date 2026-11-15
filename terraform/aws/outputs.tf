output "vpc_id" {
  value = aws_vpc.demo.id
}
output "private_subnet_id" {
  value = aws_subnet.private.id
}
output "application_security_group_id" {
  value = aws_security_group.app.id
}
