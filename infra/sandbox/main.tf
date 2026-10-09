data "aws_caller_identity" "current" {}

resource "aws_iot_thing" "device" {
  name = local.thing_name

  attributes = {
    owner      = "prototype"
    prototype  = "true"
    component  = "device"
    managed_by = "terraform-plan-only"
  }
}

resource "aws_iot_policy" "device" {
  name = "${local.sandbox_prefix}-device-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["iot:Connect"]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:client/${local.thing_name}"
        ]
      },
      {
        Effect = "Allow"
        Action = ["iot:Publish"]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topic/${local.telemetry_topic}"
        ]
      }
    ]
  })
}

resource "aws_iot_thing_principal_attachment" "device_certificate" {
  count     = var.device_certificate_arn != "" ? 1 : 0
  thing     = aws_iot_thing.device.name
  principal = var.device_certificate_arn
}

resource "aws_iot_policy_attachment" "device_policy" {
  count  = var.device_certificate_arn != "" ? 1 : 0
  policy = aws_iot_policy.device.name
  target = var.device_certificate_arn
}

resource "aws_dynamodb_table" "latest_state" {
  name         = "${local.sandbox_prefix}-latest-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "device_id"

  attribute {
    name = "device_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = false
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Name        = "iot-digital-twin-latest-state"
    Environment = var.environment
    Purpose     = "prototype-latest-device-state"
  }
}

resource "aws_iam_role" "ingest_lambda" {
  name = "${local.sandbox_prefix}-ingest-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ingest_lambda_dynamodb" {
  name = "${local.sandbox_prefix}-ingest-dynamodb"
  role = aws_iam_role.ingest_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.latest_state.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.log_prefix}:*"
      }
    ]
  })
}

resource "aws_lambda_function" "ingest" {
  function_name = "${local.sandbox_prefix}-ingest"
  role          = aws_iam_role.ingest_lambda.arn
  runtime       = "python3.12"
  handler       = "app.handler"
  filename      = "./artifacts/ingest_placeholder.zip"
  timeout       = 10

  environment {
    variables = {
      LATEST_STATE_TABLE = aws_dynamodb_table.latest_state.name
      DEVICE_TOPIC       = local.telemetry_topic
    }
  }
}

resource "aws_iot_topic_rule" "ingest" {
  name        = "${local.sandbox_prefix}-ingest-rule"
  description = "Route device telemetry to the ingestion Lambda for validation and state normalization."
  enabled     = true

  lambda {
    function_arn = aws_lambda_function.ingest.arn
  }

  sql         = "SELECT * FROM '${local.telemetry_topic}'"
  sql_version = "2016-03-23"
}

# TwinMaker resources remain a design requirement, but the current AWS provider and
# account-specific resource model should be reviewed before the first live sandbox is approved.
# This plan intentionally avoids generating a direct write path to TwinMaker without a
# confirmed connector pattern and a reviewed resource model.
