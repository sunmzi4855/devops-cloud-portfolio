# Terraform AWS Network Policy Lab

Can a Terraform pull request quietly switch a private subnet to automatic public IP assignment or open an application security group? This lab runs native Terraform plan tests against the portfolio's existing AWS network configuration, using a mocked AWS provider.

| Test case | Expected result |
| --- | --- |
| Private subnet with automatic public IP assignment disabled and no inbound app rules | Pass |
| Automatic public IP assignment enabled | Fail with `POLICY_PUBLIC_IP` |
| SSH ingress from `0.0.0.0/0` | Fail with `POLICY_APP_INGRESS` |

Each unsafe change is tested separately in a temporary copy. The verification succeeds only when the baseline passes and each variation fails with its matching diagnostic. Provider installation requires internet access. The tests use mocked AWS responses and do not deploy resources.

## Run it

Install Python 3 and Terraform 1.7 or newer. The workflow uses Terraform 1.10.5. From the repository root:

```bash
python3 terraform/aws/lab/verify_policy.py
```

Read the [Terraform test](../tests/network_policy.tftest.hcl) and the [GitHub Actions workflow](../../../.github/workflows/terraform-network-policy.yml). In Actions, open the verification step for the passing plan and the two expected policy failures.

These checks cover two specific planned settings on the subnet and app security group. A live AWS environment would need separate validation for effective reachability, related security group rules, and drift.
