variable "aws_region" {
  description = "AWS region for the sandbox prototype."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name for the sandbox resources."
  type        = string
  default     = "sandbox"
}

variable "project_name" {
  description = "Project or workload name used in resource names."
  type        = string
  default     = "iot-digital-twin"
}

variable "device_thing_name" {
  description = "AWS IoT Thing name for the prototype device."
  type        = string
  default     = "core2-aws-001"
}

variable "device_certificate_arn" {
  description = "ARN of the human-provisioned certificate attached to the Thing. Do not generate this inside Terraform state."
  type        = string
  default     = ""
}

variable "telemetry_topic" {
  description = "Restricted MQTT topic for the device telemetry stream."
  type        = string
  default     = "devices/core2-aws-001/telemetry"
}
