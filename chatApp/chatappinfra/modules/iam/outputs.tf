output "alb_controller_role_arn"      { value = aws_iam_role.alb_controller.arn }
output "external_secrets_role_arn"    { value = aws_iam_role.external_secrets.arn }
output "chatapp_role_arn"             { value = aws_iam_role.chatapp.arn }
output "cluster_autoscaler_role_arn"  { value = aws_iam_role.cluster_autoscaler.arn }
output "ebs_csi_role_arn"             { value = aws_iam_role.ebs_csi.arn }
