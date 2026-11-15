output "manifest_path" {
  value       = local_file.deployment_manifest.filename
  description = "Local file created by Terraform"
}
