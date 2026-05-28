locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 30
}

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  version  = var.kubernetes_version
  role_arn = var.cluster_role_arn

  vpc_config {
    subnet_ids              = var.private_app_subnet_ids
    security_group_ids      = [var.node_security_group_id]
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.cluster_endpoint_public_access_cidrs
  }

  # Envelope encryption for Kubernetes secrets using KMS
  encryption_config {
    provider {
      key_arn = var.kms_key_arn
    }
    resources = ["secrets"]
  }

# All control plane log types sent to CloudWatch
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [aws_cloudwatch_log_group.eks]
}

# ── OIDC provider (required for IRSA) ────────────────────────────────────────

data "tls_certificate" "eks" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

# ── Managed node group ────────────────────────────────────────────────────────

resource "aws_eks_node_group" "app" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${local.name}-app-nodes"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_app_subnet_ids

  instance_types = var.node_instance_types

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  # Force instance refresh on launch template change
  force_update_version = false

  labels = {
    role = "app"
  }

  tags = {
    Name                                                  = "${local.name}-app-nodes"
    "k8s.io/cluster-autoscaler/enabled"                   = "true"
    "k8s.io/cluster-autoscaler/${var.cluster_name}"       = "owned"
  }
}

# ── EKS add-ons ───────────────────────────────────────────────────────────────

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions["vpc-cni"]
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.app]
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions["coredns"]
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.app]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions["kube-proxy"]
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.app]
}

resource "aws_eks_addon" "pod_identity" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "eks-pod-identity-agent"
  addon_version               = var.addon_versions["eks-pod-identity-agent"]
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.app]
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.addon_versions["aws-ebs-csi-driver"]
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.app]
}
