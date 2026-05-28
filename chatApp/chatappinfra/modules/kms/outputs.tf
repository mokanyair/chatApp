output "rds_key_arn"         { value = aws_kms_key.rds.arn }
output "eks_key_arn"         { value = aws_kms_key.eks.arn }
output "secrets_key_arn"     { value = aws_kms_key.secrets.arn }
output "elasticache_key_arn" { value = aws_kms_key.elasticache.arn }
