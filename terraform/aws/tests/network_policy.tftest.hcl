mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = {
      names = ["us-east-1a"]
    }
  }
}

run "private_network_policy" {
  command = plan

  assert {
    condition     = aws_subnet.private.map_public_ip_on_launch == false
    error_message = "POLICY_PUBLIC_IP: The private subnet must disable automatic public IP assignment."
  }

  assert {
    condition     = length(aws_security_group.app.ingress) == 0
    error_message = "POLICY_APP_INGRESS: The application security group must have zero ingress rules."
  }
}
