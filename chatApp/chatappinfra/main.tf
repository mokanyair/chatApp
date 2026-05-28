data "aws_caller_identity" "current" {}

# Only queried after Phase 2 (eks_ready = true). Gives providers a known value
# at plan/import time so they never reference unknown module outputs.
data "aws_eks_cluster" "cluster" {
  count = var.eks_ready ? 1 : 0
  name  = var.cluster_name
}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

# Generate DB password once; stored in Secrets Manager
resource "random_password" "db" {
  length  = 32
  special = false
}

# Generate Redis AUTH token; stored in Secrets Manager
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false
}

# ── Networking ────────────────────────────────────────────────────────────────

module "vpc" {
  source = "./modules/vpc"

  project              = var.project
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  azs                  = var.azs
  public_subnets       = var.public_subnets
  private_app_subnets  = var.private_app_subnets
  private_data_subnets = var.private_data_subnets
  cluster_name         = var.cluster_name
}

# ── KMS keys ──────────────────────────────────────────────────────────────────

module "kms" {
  source = "./modules/kms"

  project     = var.project
  environment = var.environment
  account_id  = local.account_id
  region      = var.aws_region
}

# ── Security groups ───────────────────────────────────────────────────────────

module "security_groups" {
  source = "./modules/security_groups"

  project     = var.project
  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  vpc_cidr    = var.vpc_cidr
}

# Allow EKS cluster SG to reach RDS and Redis.
# Defined here (not in the module) to avoid a cycle:
# security_groups needs eks_nodes_sg_id → eks needs eks_nodes_sg_id → cycle.
resource "aws_security_group_rule" "eks_cluster_to_rds" {
  type                     = "ingress"
  description              = "MySQL from EKS cluster SG"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = module.security_groups.rds_sg_id
  source_security_group_id = module.eks.cluster_sg_id
}

resource "aws_security_group_rule" "eks_cluster_to_redis" {
  type                     = "ingress"
  description              = "Redis from EKS cluster SG"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = module.security_groups.elasticache_sg_id
  source_security_group_id = module.eks.cluster_sg_id
}

# ── IAM roles ─────────────────────────────────────────────────────────────────
# Note: OIDC provider ARN/URL are outputs from module.eks.
# IAM roles that reference OIDC must be created after EKS.

module "iam" {
  source = "./modules/iam"

  project           = var.project
  environment       = var.environment
  account_id        = local.account_id
  oidc_provider_arn    = module.eks.oidc_provider_arn
  oidc_provider_url    = module.eks.oidc_provider_url
  cluster_name         = var.cluster_name
  secrets_kms_key_arn  = module.kms.secrets_key_arn

  depends_on = [module.eks]
}

# ── EKS cluster ───────────────────────────────────────────────────────────────

module "eks" {
  source = "./modules/eks"

  project                 = var.project
  environment             = var.environment
  cluster_name            = var.cluster_name
  kubernetes_version      = var.kubernetes_version
  cluster_role_arn        = module.iam_bootstrap.cluster_role_arn
  node_role_arn           = module.iam_bootstrap.node_role_arn
  private_app_subnet_ids  = module.vpc.private_app_subnet_ids
  node_instance_types     = var.node_instance_types
  node_min_size           = var.node_min_size
  node_max_size           = var.node_max_size
  node_desired_size       = var.node_desired_size
  kms_key_arn             = module.kms.eks_key_arn
  node_security_group_id               = module.security_groups.eks_nodes_sg_id
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
}

# Bootstrap IAM roles that EKS needs before the cluster exists.
# These don't depend on OIDC so they can be created first.
module "iam_bootstrap" {
  source = "./modules/iam_bootstrap"

  project     = var.project
  environment = var.environment
}

# ── Aurora MySQL 8.0 ──────────────────────────────────────────────────────────

module "rds" {
  source = "./modules/rds"

  project               = var.project
  environment           = var.environment
  azs                   = var.azs
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = random_password.db.result
  db_instance_class     = var.db_instance_class
  backup_retention_days = var.db_backup_retention_days
  kms_key_arn           = module.kms.rds_key_arn
  subnet_ids            = module.vpc.private_data_subnet_ids
  security_group_id     = module.security_groups.rds_sg_id
}

# ── ElastiCache Redis 7 ───────────────────────────────────────────────────────

module "elasticache" {
  source = "./modules/elasticache"

  project           = var.project
  environment       = var.environment
  node_type         = var.redis_node_type
  num_replicas      = var.redis_num_replicas
  kms_key_arn       = module.kms.elasticache_key_arn
  subnet_ids        = module.vpc.private_data_subnet_ids
  security_group_id = module.security_groups.elasticache_sg_id
  azs               = var.azs
  auth_token        = random_password.redis_auth_token.result
}

# ── ACM certificate ───────────────────────────────────────────────────────────

module "acm" {
  source = "./modules/acm"

  domain_name      = var.domain_name
  hosted_zone_name = var.hosted_zone_name
}

# ── WAF + ALB access logs bucket ─────────────────────────────────────────────

module "waf" {
  source = "./modules/waf"

  project     = var.project
  environment = var.environment
  account_id  = local.account_id
  aws_region  = var.aws_region
  rate_limit  = 2000
}

# ── Secrets Manager ───────────────────────────────────────────────────────────

module "secrets" {
  source = "./modules/secrets"

  project     = var.project
  environment = var.environment
  kms_key_arn = module.kms.secrets_key_arn
  db_username      = var.db_username
  db_password      = random_password.db.result
  redis_auth_token = random_password.redis_auth_token.result
}

# ── Monitoring (CloudWatch alarms + SNS) ─────────────────────────────────────

module "monitoring" {
  source = "./modules/monitoring"

  project     = var.project
  environment = var.environment
  aws_region  = var.aws_region
  alert_email = var.alert_email

  rds_cluster_identifier     = module.rds.cluster_identifier
  rds_writer_instance_id     = module.rds.writer_instance_id
  redis_replication_group_id = module.elasticache.replication_group_id
  waf_name                   = module.waf.web_acl_name
  eks_node_asg_name          = module.eks.node_asg_name
  eks_node_min_size          = var.node_min_size
}

# ── Generated Helm secrets file ───────────────────────────────────────────────
# Written to ../awschatapp-platform/values-prod-secrets.yaml after apply.
# Keeps Helm credentials in sync with Terraform-generated secrets automatically.

resource "local_file" "helm_values_secrets" {
  filename        = "${path.module}/../awschatapp-platform/values-prod-secrets.yaml"
  file_permission = "0600"

  content = <<-EOT
    # Auto-generated by Terraform — do not edit manually.
    # Run `terraform apply` to refresh after secret rotation.
    api:
      secretKey: "${module.secrets.app_secret_key}"

    db:
      password: "${module.secrets.db_password}"

    redis:
      authToken: "${module.secrets.redis_auth_token}"
  EOT
}

# ── Generated Helm values file ────────────────────────────────────────────────
# Written to ../awschatapp-platform/values-prod-infra.yaml after apply.

resource "local_file" "helm_values_infra" {
  filename        = "${path.module}/../awschatapp-platform/values-prod-infra.yaml"
  file_permission = "0600"

  content = templatefile("${path.module}/templates/helm-values.tftpl", {
    domain_name        = var.domain_name
    db_host            = module.rds.cluster_endpoint
    db_read_host       = module.rds.reader_endpoint
    db_name            = var.db_name
    db_username        = var.db_username
    redis_host         = module.elasticache.primary_endpoint
    public_subnet_ids  = join(",", module.vpc.public_subnet_ids)
    certificate_arn    = module.acm.certificate_arn
    waf_arn            = module.waf.web_acl_arn
    alb_logs_bucket    = module.waf.alb_logs_bucket
    account_id         = local.account_id
    replica_count      = var.app_replica_count
    image_repo         = var.app_image_repository
    image_tag          = var.app_image_tag
  })
}
