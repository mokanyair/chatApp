locals {
  name = "${var.project}-${var.environment}"
}

# generates a JSON IAM policy document dynamically or read external existing information

data "aws_iam_policy_document" "kms" {
  statement {
    sid     = "Enable IAM root access"
    effect  = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "Allow CloudWatch Logs"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logs.${var.region}.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
      "kms:GenerateDataKey*", "kms:DescribeKey",
    ]
    resources = ["*"]
  }
}

resource "aws_kms_key" "rds" {
  description             = "${local.name} RDS encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms.json
  tags                    = { Name = "${local.name}-kms-rds" }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

resource "aws_kms_key" "eks" {
  description             = "${local.name} EKS secrets encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms.json
  tags                    = { Name = "${local.name}-kms-eks" }
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

resource "aws_kms_key" "secrets" {
  description             = "${local.name} Secrets Manager encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms.json
  tags                    = { Name = "${local.name}-kms-secrets" }
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${local.name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_kms_key" "elasticache" {
  description             = "${local.name} ElastiCache at-rest encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms.json
  tags                    = { Name = "${local.name}-kms-elasticache" }
}

resource "aws_kms_alias" "elasticache" {
  name          = "alias/${local.name}-elasticache"
  target_key_id = aws_kms_key.elasticache.key_id
}
