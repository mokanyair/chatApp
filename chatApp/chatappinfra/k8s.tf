# ── StorageClass — EBS CSI (gp2) ─────────────────────────────────────────────
# EKS 1.23+ migrates in-tree EBS to the CSI driver (ebs.csi.aws.com).
# This class is set as default so PVCs without an explicit class get EBS volumes.

resource "kubernetes_storage_class_v1" "gp2_csi" {
  metadata {
    name = "gp2"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = "true"
    }
  }
  storage_provisioner    = "ebs.csi.aws.com"
  reclaim_policy         = "Delete"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  parameters = {
    type = "gp2"
  }
  depends_on = [module.eks]

  lifecycle {
    ignore_changes = [metadata[0].annotations]
  }
}

# ── Namespaces ────────────────────────────────────────────────────────────────

resource "kubernetes_namespace" "chatapp" {
  metadata {
    name = "chatapp"
    labels = {
      "pod-security.kubernetes.io/enforce" = "restricted"
      "pod-security.kubernetes.io/warn"    = "restricted"
    }
  }
  depends_on = [module.eks]
}

resource "kubernetes_namespace" "external_secrets" {
  metadata { name = "external-secrets" }
  depends_on = [module.eks]
}

resource "kubernetes_namespace" "monitoring" {
  metadata { name = "monitoring" }
  depends_on = [module.eks]
}

# ── Service accounts ──────────────────────────────────────────────────────────

resource "kubernetes_service_account" "alb_controller" {
  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = module.iam.alb_controller_role_arn
    }
  }
  depends_on = [module.eks, module.iam]
}

resource "kubernetes_service_account" "external_secrets" {
  metadata {
    name      = "external-secrets"
    namespace = kubernetes_namespace.external_secrets.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = module.iam.external_secrets_role_arn
    }
  }
  depends_on = [module.eks, module.iam]
}

resource "kubernetes_service_account" "chatapp" {
  metadata {
    name      = "chatapp"
    namespace = kubernetes_namespace.chatapp.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = module.iam.chatapp_role_arn
    }
  }
  depends_on = [kubernetes_namespace.chatapp, module.iam]
}

resource "kubernetes_service_account" "cluster_autoscaler" {
  metadata {
    name      = "cluster-autoscaler"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = module.iam.cluster_autoscaler_role_arn
    }
  }
  depends_on = [module.eks, module.iam]
}

# ── RDS CA certificate ────────────────────────────────────────────────────────
# Upload global-bundle.pem from the local file (downloaded separately).

resource "kubernetes_secret" "rds_ca_cert" {
  metadata {
    name      = "rds-ca-cert"
    namespace = kubernetes_namespace.chatapp.metadata[0].name
  }
  data = {
    "global-bundle.pem" = fileexists("${path.module}/global-bundle.pem") ? file("${path.module}/global-bundle.pem") : ""
  }
  type       = "Opaque"
  depends_on = [kubernetes_namespace.chatapp]
}

# ── ESO ClusterSecretStore → AWS Secrets Manager ──────────────────────────────

resource "kubernetes_manifest" "cluster_secret_store" {
  manifest = {
    apiVersion = "external-secrets.io/v1beta1"
    kind       = "ClusterSecretStore"
    metadata   = { name = "aws-secrets-manager" }
    spec = {
      provider = {
        aws = {
          service = "SecretsManager"
          region  = var.aws_region
          auth = {
            jwt = {
              serviceAccountRef = {
                name      = "external-secrets"
                namespace = "external-secrets"
              }
            }
          }
        }
      }
    }
  }
  depends_on = [helm_release.external_secrets]
}

# ── ESO ExternalSecret — syncs Secrets Manager → chatapp-secret ──────────────

resource "kubernetes_manifest" "external_secret_chatapp" {
  manifest = {
    apiVersion = "external-secrets.io/v1beta1"
    kind       = "ExternalSecret"
    metadata = {
      name      = "chatapp-external-secret"
      namespace = kubernetes_namespace.chatapp.metadata[0].name
    }
    spec = {
      refreshInterval = "1h"
      secretStoreRef  = { name = "aws-secrets-manager", kind = "ClusterSecretStore" }
      target          = { name = "chatapp-aws-credentials", creationPolicy = "Owner" }
      data = [
        {
          secretKey = "DB_PASSWORD"
          remoteRef = { key = module.secrets.db_secret_name, property = "password" }
        },
        {
          secretKey = "SECRET_KEY"
          remoteRef = { key = module.secrets.app_secret_name, property = "secret_key" }
        },
      ]
    }
  }
  depends_on = [kubernetes_manifest.cluster_secret_store, kubernetes_namespace.chatapp]
}

# ── Resource controls ─────────────────────────────────────────────────────────

resource "kubernetes_resource_quota_v1" "chatapp" {
  metadata {
    name      = "chatapp-quota"
    namespace = kubernetes_namespace.chatapp.metadata[0].name
  }
  spec {
    hard = {
      "requests.cpu"    = "4"
      "requests.memory" = "4Gi"
      "limits.cpu"      = "8"
      "limits.memory"   = "8Gi"
      "pods"            = "20"
    }
  }
  depends_on = [kubernetes_namespace.chatapp]
}

resource "kubernetes_limit_range_v1" "chatapp" {
  metadata {
    name      = "chatapp-limits"
    namespace = kubernetes_namespace.chatapp.metadata[0].name
  }
  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "512Mi"
      }
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
      max = {
        cpu    = "2"
        memory = "2Gi"
      }
    }
  }
  depends_on = [kubernetes_namespace.chatapp]
}

# ── PodDisruptionBudget ───────────────────────────────────────────────────────

resource "kubernetes_pod_disruption_budget_v1" "chatapp" {
  metadata {
    name      = "chatapp-pdb"
    namespace = kubernetes_namespace.chatapp.metadata[0].name
  }
  spec {
    min_available = 1
    selector {
      match_labels = { "app.kubernetes.io/name" = "chat-api" }
    }
  }
  depends_on = [kubernetes_namespace.chatapp]
}

# ── NetworkPolicy ─────────────────────────────────────────────────────────────

resource "kubernetes_network_policy" "chatapp" {
  metadata {
    name      = "chatapp-netpol"
    namespace = kubernetes_namespace.chatapp.metadata[0].name
  }
  spec {
    pod_selector {
      match_labels = { "app.kubernetes.io/name" = "chat-api" }
    }
    policy_types = ["Ingress", "Egress"]

    ingress {
      ports {
        protocol = "TCP"
        port     = "8000"
      }
    }

    egress {
      ports {
        protocol = "UDP"
        port     = "53"
      }
    }
    egress {
      ports {
        protocol = "TCP"
        port     = "3306"
      }
    }
    egress {
      ports {
        protocol = "TCP"
        port     = "6379"
      }
    }
    egress {
      ports {
        protocol = "TCP"
        port     = "443"
      }
    }
  }
  depends_on = [kubernetes_namespace.chatapp]
}
