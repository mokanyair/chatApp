variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name used in resource naming and tagging"
  type        = string
  default     = "chatapp"
}

variable "environment" {
  description = "Deployment environment (prod, staging)"
  type        = string
  default     = "prod"
}

# ── Networking ────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  type    = string
  default = "10.1.0.0/16"
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "public_subnets" {
  description = "CIDRs for public subnets (ALB placement)"
  type        = list(string)
  default     = ["10.1.0.0/24", "10.1.1.0/24"]
}

variable "private_app_subnets" {
  description = "CIDRs for private app subnets (EKS nodes)"
  type        = list(string)
  default     = ["10.1.8.0/22", "10.1.12.0/22"]
}

variable "private_data_subnets" {
  description = "CIDRs for private data subnets (RDS, ElastiCache)"
  type        = list(string)
  default     = ["10.1.20.0/24", "10.1.21.0/24"]
}

# ── EKS ──────────────────────────────────────────────────────────────────────

variable "cluster_name" {
  type    = string
  default = "chatapp-prod-cluster"
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API server"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "kubernetes_version" {
  type    = string
  default = "1.31"
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 10
}

variable "node_desired_size" {
  type    = number
  default = 2
}

# ── Database ─────────────────────────────────────────────────────────────────

variable "db_name" {
  type    = string
  default = "chatdb"
}

variable "db_username" {
  type    = string
  default = "admin"
}

variable "db_instance_class" {
  description = "Aurora instance class for writer and reader"
  type        = string
  default     = "db.t3.medium"
}

variable "db_backup_retention_days" {
  type    = number
  default = 30
}

# ── ElastiCache ───────────────────────────────────────────────────────────────

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "redis_num_replicas" {
  description = "Number of replica nodes per shard (1 = primary + 1 replica)"
  type        = number
  default     = 1
}

# ── DNS / TLS ─────────────────────────────────────────────────────────────────

variable "domain_name" {
  description = "FQDN for the application (e.g. chat.example.com)"
  type        = string
}

variable "hosted_zone_name" {
  description = "Route53 hosted zone name (e.g. example.com)"
  type        = string
}

# ── Application ───────────────────────────────────────────────────────────────

variable "app_image_repository" {
  type    = string
  default = "morganokanyair/chat-api"
}

variable "app_image_tag" {
  description = "Pin to a specific digest or semver tag in production — no default, must be set explicitly"
  type        = string
}

variable "app_replica_count" {
  type    = number
  default = 3
}

# ── Deployment phasing ────────────────────────────────────────────────────────

variable "eks_ready" {
  description = "Set to true after Phase 2 (EKS cluster exists). Enables helm/kubernetes provider auth."
  type        = bool
  default     = false
}

# ── Observability ─────────────────────────────────────────────────────────────

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = ""
}
