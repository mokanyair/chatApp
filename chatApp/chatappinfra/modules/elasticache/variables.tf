variable "project"          { type = string }
variable "environment"      { type = string }
variable "node_type"        { type = string }
variable "num_replicas"     { type = number }
variable "kms_key_arn"      { type = string }
variable "subnet_ids"       { type = list(string) }
variable "security_group_id" { type = string }
variable "azs"              { type = list(string) }
variable "auth_token" {
  type      = string
  sensitive = true
}
variable "snapshot_retention_days" {
  type    = number
  default = 30
}
