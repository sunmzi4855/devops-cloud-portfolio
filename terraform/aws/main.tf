terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Demonstration-only network foundation.
# Do not apply unless you control the AWS account and understand cost/security implications.
resource "aws_vpc" "demo" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.project_name}-vpc", Environment = "demo" }
}

resource "aws_subnet" "private" {
  vpc_id                  = aws_vpc.demo.id
  cidr_block              = var.subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = false
  tags = { Name = "${var.project_name}-private" }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_security_group" "app" {
  name_prefix = "${var.project_name}-app-"
  description = "Demo application security group with no ingress"
  vpc_id      = aws_vpc.demo.id

  # No ingress is allowed in this illustrative network foundation.
  # Add narrowly scoped rules only when actual application requirements are known.
  tags = { Name = "${var.project_name}-app" }
}
