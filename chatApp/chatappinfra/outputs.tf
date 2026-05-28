output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "rds_writer_endpoint" {
  value       = module.rds.cluster_endpoint
  description = "Aurora writer endpoint — use for DATABASE_URL"
}

output "rds_reader_endpoint" {
  value       = module.rds.reader_endpoint
  description = "Aurora reader endpoint — use for read-only replicas"
}

output "redis_configuration_endpoint" {
  value       = module.elasticache.configuration_endpoint
  description = "ElastiCache cluster config endpoint — use for REDIS_URL"
}

output "acm_certificate_arn" {
  value       = module.acm.certificate_arn
  description = "ACM certificate ARN — used by ALB HTTPS listener"
}

output "waf_web_acl_arn" {
  value       = module.waf.web_acl_arn
  description = "WAF WebACL ARN — annotated on the ALB Ingress"
}

output "alb_logs_bucket" {
  value       = module.waf.alb_logs_bucket
  description = "S3 bucket for ALB access logs"
}

output "db_secret_arn" {
  value       = module.secrets.db_secret_arn
  description = "Secrets Manager ARN for DB credentials"
}

output "app_secret_arn" {
  value       = module.secrets.app_secret_arn
  description = "Secrets Manager ARN for app secret key"
}

output "helm_deploy_command" {
  value = <<-EOT
    # Update kubeconfig
    aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}

    # Download RDS CA bundle (if not already present)
    curl -sL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o global-bundle.pem

    # Apply with generated values
    helm upgrade --install chatapp ../awschatapp-platform \
      --values ../awschatapp-platform/values.yaml \
      --values ../awschatapp-platform/values-prod-infra.yaml \
      --values ../awschatapp-platform/values-prod-secrets.yaml \
      -n chatapp --create-namespace
  EOT
  description = "Helm deploy command after terraform apply"
}
