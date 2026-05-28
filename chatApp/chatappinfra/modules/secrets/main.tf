locals {
  name   = "${var.project}-${var.environment}"
  prefix = "${var.project}/${var.environment}"
}

# ── DB credentials ────────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "db" {
  name                    = "${local.prefix}/db-credentials"
  description             = "${local.name} Aurora MySQL credentials"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 7
  tags                    = { Name = "${local.name}-db-secret" }
}

resource "aws_secretsmanager_secret_rotation" "db" {
  count               = var.rotation_lambda_arn != null ? 1 : 0
  secret_id           = aws_secretsmanager_secret.db.id
  rotation_lambda_arn = var.rotation_lambda_arn
  rotation_rules {
    automatically_after_days = 30
  }
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
  })
}

# ── Redis AUTH token ─────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "redis" {
  name                    = "${local.prefix}/redis-auth-token"
  description             = "${local.name} ElastiCache Redis AUTH token"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 7
  tags                    = { Name = "${local.name}-redis-secret" }
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id     = aws_secretsmanager_secret.redis.id
  secret_string = jsonencode({ auth_token = var.redis_auth_token })
}

# ── App secret key ────────────────────────────────────────────────────────────

resource "random_password" "app_secret_key" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.prefix}/app-config"
  description             = "${local.name} application secret key"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 7
  tags                    = { Name = "${local.name}-app-secret" }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id     = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({ secret_key = random_password.app_secret_key.result })
}

resource "aws_secretsmanager_secret_rotation" "app" {
  count               = var.rotation_lambda_arn != null ? 1 : 0
  secret_id           = aws_secretsmanager_secret.app.id
  rotation_lambda_arn = var.rotation_lambda_arn
  rotation_rules {
    automatically_after_days = 30
  }
}
