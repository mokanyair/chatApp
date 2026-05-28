# ── Kubernetes operators installed via Helm ───────────────────────────────────
# All depend on module.eks. Run `terraform apply -target=module.eks` first.

resource "helm_release" "aws_lb_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.8.3"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }
  set {
    name  = "serviceAccount.create"
    value = "false"
  }
  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }
  set {
    name  = "region"
    value = var.aws_region
  }
  set {
    name  = "vpcId"
    value = module.vpc.vpc_id
  }

  depends_on = [module.eks, kubernetes_service_account.alb_controller]
}

resource "helm_release" "external_secrets" {
  name             = "external-secrets"
  repository       = "https://charts.external-secrets.io"
  chart            = "external-secrets"
  namespace        = "external-secrets"
  version          = "0.9.20"
  create_namespace = true

  # Only disable creation for the main controller SA (it's pre-created with IRSA annotation).
  # Webhook and cert-controller don't need IRSA — let Helm manage their SAs.
  set {
    name  = "serviceAccount.create"
    value = "false"
  }
  set {
    name  = "serviceAccount.name"
    value = "external-secrets"
  }

  depends_on = [module.eks, kubernetes_service_account.external_secrets]
}

resource "helm_release" "kube_prometheus_stack" {
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  version          = "61.3.2"
  create_namespace = false
  timeout          = 600

  # Tuned for t3.medium nodes (2 vCPU, 4Gi each).
  # Disables EKS-inaccessible control-plane scrapers.
  values = [<<-YAML
    # ── Prometheus ──────────────────────────────────────────────────────────
    prometheus:
      prometheusSpec:
        retention: 7d
        retentionSize: "9GB"
        scrapeInterval: "30s"
        evaluationInterval: "30s"

        # Discover ServiceMonitors and PrometheusRules in all namespaces
        serviceMonitorSelectorNilUsesHelmValues: false
        serviceMonitorSelector: {}
        serviceMonitorNamespaceSelector: {}
        ruleSelector: {}
        ruleNamespaceSelector: {}

        resources:
          requests:
            cpu: 300m
            memory: 512Mi
          limits:
            cpu: 750m
            memory: 1Gi

        storageSpec:
          volumeClaimTemplate:
            spec:
              storageClassName: gp2
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: 10Gi

    # ── Grafana ─────────────────────────────────────────────────────────────
    grafana:
      adminPassword: "chatapp-grafana-admin"
      defaultDashboardsTimezone: browser

      resources:
        requests:
          cpu: 50m
          memory: 128Mi
        limits:
          cpu: 200m
          memory: 256Mi

      # Sidecar picks up dashboard ConfigMaps from all namespaces
      sidecar:
        dashboards:
          enabled: true
          searchNamespace: ALL
          label: grafana_dashboard

      grafana.ini:
        server:
          root_url: "%(protocol)s://%(domain)s/grafana"
          serve_from_sub_path: true

    # ── Alertmanager ────────────────────────────────────────────────────────
    alertmanager:
      alertmanagerSpec:
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 100m
            memory: 128Mi

    # ── kube-state-metrics ──────────────────────────────────────────────────
    kube-state-metrics:
      resources:
        requests:
          cpu: 20m
          memory: 64Mi
        limits:
          cpu: 100m
          memory: 128Mi

    # ── node-exporter ────────────────────────────────────────────────────────
    prometheus-node-exporter:
      resources:
        requests:
          cpu: 10m
          memory: 32Mi
        limits:
          cpu: 50m
          memory: 64Mi

    # ── Disable EKS-inaccessible control-plane scrapers ─────────────────────
    kubeEtcd:
      enabled: false
    kubeScheduler:
      enabled: false
    kubeControllerManager:
      enabled: false
    kubeProxy:
      enabled: false
  YAML
  ]

  depends_on = [module.eks, kubernetes_namespace.monitoring]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  namespace  = "kube-system"
  version    = "3.12.1"

  depends_on = [module.eks]
}

resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  namespace  = "kube-system"
  version    = "9.37.0"

  set {
    name  = "autoDiscovery.clusterName"
    value = module.eks.cluster_name
  }
  set {
    name  = "awsRegion"
    value = var.aws_region
  }
  set {
    name  = "rbac.serviceAccount.create"
    value = "false"
  }
  set {
    name  = "rbac.serviceAccount.name"
    value = "cluster-autoscaler"
  }
  set {
    name  = "extraArgs.balance-similar-node-groups"
    value = "true"
  }
  set {
    name  = "extraArgs.skip-nodes-with-system-pods"
    value = "false"
  }

  depends_on = [module.eks, kubernetes_service_account.cluster_autoscaler]
}
