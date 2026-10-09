locals {
  sandbox_prefix  = "${var.project_name}-${var.environment}"
  thing_name      = var.device_thing_name
  telemetry_topic = var.telemetry_topic
  log_prefix      = "/aws/lambda/${var.project_name}-ingest"
}
