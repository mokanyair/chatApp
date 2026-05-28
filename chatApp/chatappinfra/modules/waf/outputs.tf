output "web_acl_arn"      { value = aws_wafv2_web_acl.this.arn }
output "web_acl_name"     { value = aws_wafv2_web_acl.this.name }
output "alb_logs_bucket"  { value = aws_s3_bucket.alb_logs.id }
