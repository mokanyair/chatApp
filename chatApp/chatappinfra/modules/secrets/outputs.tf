output "db_secret_arn"    { value = aws_secretsmanager_secret.db.arn }
output "db_secret_name"   { value = aws_secretsmanager_secret.db.name }
output "app_secret_arn"     { value = aws_secretsmanager_secret.app.arn }
output "app_secret_name"    { value = aws_secretsmanager_secret.app.name }
output "redis_secret_arn"   { value = aws_secretsmanager_secret.redis.arn }
output "redis_secret_name"  { value = aws_secretsmanager_secret.redis.name }

output "db_password" {
  value     = var.db_password
  sensitive = true
}
output "redis_auth_token" {
  value     = var.redis_auth_token
  sensitive = true
}
output "app_secret_key" {
  value     = random_password.app_secret_key.result
  sensitive = true
}
