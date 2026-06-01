locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_db_subnet_group" "this" {
  name        = "${local.name}-rds-subnet-group"
  description = "Aurora MySQL subnet group"
  subnet_ids  = var.subnet_ids
  tags        = { Name = "${local.name}-rds-subnet-group" }
}

resource "aws_rds_cluster_parameter_group" "this" {
  name        = "${local.name}-aurora-mysql8-cluster-pg"
  family      = "aurora-mysql8.0"
  description = "Aurora MySQL 8.0 cluster parameter group"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }
  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }
  parameter {
    name  = "slow_query_log"
    value = "1"
  }
  parameter {
    name  = "long_query_time"
    value = "2"
  }
  parameter {
    name  = "general_log"
    value = "0"
  }
}

resource "aws_db_parameter_group" "this" {
  name   = "${local.name}-aurora-mysql8-db-pg"
  family = "aurora-mysql8.0"
}

resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_rds_cluster" "this" {
  cluster_identifier = "${local.name}-db"
  engine             = "aurora-mysql"
  engine_version     = "8.0.mysql_aurora.3.08.2"
  database_name      = var.db_name
  master_username    = var.db_username
  master_password    = var.db_password

  db_subnet_group_name            = aws_db_subnet_group.this.name
  vpc_security_group_ids          = [var.security_group_id]
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.this.name

  # Encryption at rest
  storage_encrypted = true
  kms_key_id        = var.kms_key_arn

  # Protection — deletion_protection and final snapshot both disabled for clean teardown
  deletion_protection   = false
  skip_final_snapshot   = true
  copy_tags_to_snapshot = true

  # Backup
  backup_retention_period      = var.backup_retention_days
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "sun:05:00-sun:06:00"

  # Logging → CloudWatch
  enabled_cloudwatch_logs_exports = ["audit", "error", "slowquery"]

  apply_immediately = false

  tags = { Name = "${local.name}-db" }
}

resource "aws_rds_cluster_instance" "writer" {
  identifier         = "${local.name}-db-writer"
  cluster_identifier = aws_rds_cluster.this.id
  instance_class     = var.db_instance_class
  engine             = aws_rds_cluster.this.engine
  engine_version     = aws_rds_cluster.this.engine_version

  availability_zone    = var.azs[0]
  db_subnet_group_name = aws_db_subnet_group.this.name
  db_parameter_group_name = aws_db_parameter_group.this.name

  monitoring_interval          = 60
  monitoring_role_arn          = aws_iam_role.rds_monitoring.arn
  performance_insights_enabled = false

  auto_minor_version_upgrade = true
  tags                       = { Name = "${local.name}-db-writer" }
}

#resource "aws_rds_cluster_instance" "reader" {
 # identifier         = "${local.name}-db-reader"
 # cluster_identifier = aws_rds_cluster.this.id
 # instance_class     = var.db_instance_class
 # engine             = aws_rds_cluster.this.engine
 # engine_version     = aws_rds_cluster.this.engine_version

 # availability_zone    = var.azs[1]
 # db_subnet_group_name = aws_db_subnet_group.this.name
 # db_parameter_group_name = aws_db_parameter_group.this.name

 # monitoring_interval          = 60
 # monitoring_role_arn          = aws_iam_role.rds_monitoring.arn
 # performance_insights_enabled = false

 # auto_minor_version_upgrade = true
 # tags                       = { Name = "${local.name}-db-reader" }
#}
