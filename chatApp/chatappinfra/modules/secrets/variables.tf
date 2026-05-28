variable "project"     { type = string }
variable "environment" { type = string }
variable "kms_key_arn" { type = string }
variable "db_username" { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "redis_auth_token" {
  type      = string
  sensitive = true
}
variable "rotation_lambda_arn"    {
  description = "ARN of the Secrets Manager rotation Lambda (deploy via SAR before enabling)"
  type        = string
  default     = null
}
