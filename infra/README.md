# Infrastructure

Put infrastructure-as-code here only when the business solution requires it.

Recommended approach:

- one clearly documented entry point
- separate environment configuration from reusable modules
- no secrets in Terraform variables or committed state
- `plan` before changes
- destructive operations require explicit human authorization

Do not add AWS services merely because the template is often used for cloud projects. Start from the business requirement in `PROJECT_BRIEF.md`.
