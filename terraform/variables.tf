variable "service_name" {
  type        = string
  description = "Service name for the generated manifest"
  default     = "cloud-devops-demo"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "development"
}
