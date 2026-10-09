output "sandbox_prefix" {
  description = "Shared prefix used for sandbox resources."
  value       = local.sandbox_prefix
}

output "device_topic" {
  description = "Telemetry topic the prototype device is expected to publish to."
  value       = local.telemetry_topic
}

output "thing_name" {
  description = "Thing name that must be bound to the human-provisioned device certificate."
  value       = local.thing_name
}
