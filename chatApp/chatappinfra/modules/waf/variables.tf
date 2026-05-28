variable "project"     { type = string }
variable "environment" { type = string }
variable "account_id"  { type = string }
variable "rate_limit" {
  type    = number
  default = 2000
}
variable "aws_region"  { type = string }
