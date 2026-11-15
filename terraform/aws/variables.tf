variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

variable "project_name" {
  type        = string
  default     = "devops-portfolio"
  description = "Prefix for demo cloud resources"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.40.0.0/16"
  description = "VPC CIDR"
}

variable "subnet_cidr" {
  type        = string
  default     = "10.40.1.0/24"
  description = "Private subnet CIDR"
}
