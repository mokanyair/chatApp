variable "project"               { type = string }
variable "environment"           { type = string }
variable "azs"                   { type = list(string) }
variable "db_name"               { type = string }
variable "db_username"           { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "db_instance_class"     { type = string }
variable "backup_retention_days" { type = number }
variable "kms_key_arn"           { type = string }
variable "subnet_ids"            { type = list(string) }
variable "security_group_id"     { type = string }
