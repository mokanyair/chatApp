output "cluster_endpoint"         { value = aws_rds_cluster.this.endpoint }
output "reader_endpoint"          { value = aws_rds_cluster.this.reader_endpoint }
output "cluster_identifier"       { value = aws_rds_cluster.this.cluster_identifier }
output "database_name"            { value = aws_rds_cluster.this.database_name }
output "writer_instance_id"       { value = aws_rds_cluster_instance.writer.identifier }
