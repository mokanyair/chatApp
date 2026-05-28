output "configuration_endpoint"   { value = aws_elasticache_replication_group.this.configuration_endpoint_address }
output "primary_endpoint"        { value = aws_elasticache_replication_group.this.primary_endpoint_address }
output "port"                    { value = aws_elasticache_replication_group.this.port }
output "replication_group_id"    { value = aws_elasticache_replication_group.this.id }
