locals {
  name = "${var.project}-${var.environment}"
}

# ── SNS topic for all alerts ──────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"
  tags = { Name = "${local.name}-alerts" }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ── RDS alarms ────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name}-rds-cpu-high"
  alarm_description   = "RDS writer CPU utilisation above 80%"
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  dimensions          = { DBInstanceIdentifier = var.rds_writer_instance_id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.name}-rds-connections-high"
  alarm_description   = "RDS cluster connections above 200"
  namespace           = "AWS/RDS"
  metric_name         = "DatabaseConnections"
  dimensions          = { DBClusterIdentifier = var.rds_cluster_identifier }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 200
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = "${local.name}-rds-storage-low"
  alarm_description   = "RDS writer free local storage below 10 GiB"
  namespace           = "AWS/RDS"
  metric_name         = "FreeLocalStorage"
  dimensions          = { DBInstanceIdentifier = var.rds_writer_instance_id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 10737418240 # 10 GiB in bytes
  comparison_operator = "LessThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

# ── ElastiCache alarms ────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${local.name}-redis-cpu-high"
  alarm_description   = "Redis CPU utilisation above 75%"
  namespace           = "AWS/ElastiCache"
  metric_name         = "CPUUtilization"
  dimensions          = { ReplicationGroupId = var.redis_replication_group_id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 75
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${local.name}-redis-evictions"
  alarm_description   = "Redis evictions above 100 — memory pressure"
  namespace           = "AWS/ElastiCache"
  metric_name         = "Evictions"
  dimensions          = { ReplicationGroupId = var.redis_replication_group_id }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 100
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "redis_replication_lag" {
  alarm_name          = "${local.name}-redis-replication-lag"
  alarm_description   = "Redis replica lag above 60 seconds"
  namespace           = "AWS/ElastiCache"
  metric_name         = "ReplicationLag"
  dimensions          = { ReplicationGroupId = var.redis_replication_group_id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 60
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

# ── EKS node alarms ──────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "eks_node_cpu" {
  alarm_name          = "${local.name}-eks-node-cpu-high"
  alarm_description   = "EKS node average CPU above 80% for 10 minutes"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { AutoScalingGroupName = var.eks_node_asg_name }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "eks_nodes_in_service" {
  alarm_name          = "${local.name}-eks-nodes-below-minimum"
  alarm_description   = "EKS in-service node count dropped below configured minimum"
  namespace           = "AWS/AutoScaling"
  metric_name         = "GroupInServiceInstances"
  dimensions          = { AutoScalingGroupName = var.eks_node_asg_name }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  threshold           = var.eks_node_min_size
  comparison_operator = "LessThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "breaching"
}

# ── WAF alarms ────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests" {
  alarm_name          = "${local.name}-waf-blocked-spike"
  alarm_description   = "WAF blocked request rate above 1000 in 5 minutes"
  namespace           = "AWS/WAFV2"
  metric_name         = "BlockedRequests"
  dimensions = {
    WebACL = var.waf_name
    Rule   = "ALL"
    Region = var.aws_region
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1000
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}
