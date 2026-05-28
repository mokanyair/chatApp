variable "project"              { type = string }
variable "environment"          { type = string }
variable "cluster_name"         { type = string }
variable "kubernetes_version"   { type = string }
variable "cluster_role_arn"     { type = string }
variable "node_role_arn"        { type = string }
variable "private_app_subnet_ids" { type = list(string) }
variable "node_instance_types"  { type = list(string) }
variable "node_min_size"        { type = number }
variable "node_max_size"        { type = number }
variable "node_desired_size"    { type = number }
variable "kms_key_arn"          { type = string }
variable "node_security_group_id" { type = string }

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "addon_versions" {
  description = "Pinned versions for EKS managed add-ons"
  type        = map(string)
  default = {
    vpc-cni                = "v1.18.1-eksbuild.3"
    coredns                = "v1.11.3-eksbuild.1"
    kube-proxy             = "v1.31.2-eksbuild.3"
    eks-pod-identity-agent = "v1.3.4-eksbuild.1"
    aws-ebs-csi-driver     = "v1.60.0-eksbuild.1"
  }
}
