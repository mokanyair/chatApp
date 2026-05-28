variable "project"     { type = string }
variable "environment" { type = string }
variable "aws_region"  { type = string }
variable "alert_email" { type = string }

variable "rds_cluster_identifier"  { type = string }
variable "rds_writer_instance_id"  { type = string }
variable "redis_replication_group_id" { type = string }
variable "waf_name"                { type = string }
variable "eks_node_asg_name"      { type = string }
variable "eks_node_min_size"      { type = number }
