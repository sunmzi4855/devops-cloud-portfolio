# Project 4 — AWS Network Infrastructure with Terraform

A declarative, inspectable AWS network example including a VPC, private subnet, and restrictive security group.

**Default stance:** This is source code only. Nothing is deployed by pushing it to GitHub. Never upload AWS access keys or Terraform state.

## Safe review

```bash
cd terraform/aws
terraform init -backend=false
terraform fmt -check
terraform validate
```

`terraform plan` requires AWS credentials with appropriate permissions and may contact AWS; it does not deploy resources. `terraform apply` can create billable cloud resources or change an account and is **not part of the GitHub CI workflow**.

There are no NAT gateways, EC2 instances, load balancers, or database instances in this example. A subnet without an internet gateway route does not automatically have internet access.

## Architecture

```text
AWS Region
  └── VPC (10.40.0.0/16)
      ├── Private subnet (10.40.1.0/24)
      └── Security group (no ingress)
```

For production, add separate availability zones, network ACL policy, logging, encryption, backend state locking, change approvals and explicit cost controls.
