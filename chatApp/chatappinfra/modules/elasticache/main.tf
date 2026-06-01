locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_elasticache_subnet_group" "this" {
  name        = "${local.name}-redis-subnet-group"
  description = "ElastiCache Redis subnet group"
  subnet_ids  = var.subnet_ids
  tags        = { Name = "${local.name}-redis-subnet-group" }
}

resource "aws_elasticache_parameter_group" "this" {
  name   = "${local.name}-redis7-pg"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${local.name}-redis"
  description          = "${local.name} Redis cluster"

  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.node_type
  num_cache_clusters   = var.num_replicas + 1  # primary + replicas
  parameter_group_name = aws_elasticache_parameter_group.this.name
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [var.security_group_id]

  automatic_failover_enabled = false
  multi_az_enabled           = false

  # Encryption
  at_rest_encryption_enabled = true
  kms_key_id                 = var.kms_key_arn
  transit_encryption_enabled = true
  auth_token                 = var.auth_token

  # Maintenance
  snapshot_retention_limit     = var.snapshot_retention_days
  snapshot_window              = "04:00-05:00"
  maintenance_window           = "sun:06:00-sun:07:00"
  auto_minor_version_upgrade   = true

  apply_immediately = false

  tags = { Name = "${local.name}-redis" }
}
