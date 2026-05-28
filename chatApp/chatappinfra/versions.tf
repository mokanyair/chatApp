terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }

  
  backend "s3" {
    bucket         = "chatapp-remotestates3"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "chatapp-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Helm + Kubernetes providers: set eks_ready=true in terraform.tfvars after
# Phase 2 completes so these providers connect to the real cluster.
provider "helm" {
  kubernetes {
    host                   = var.eks_ready ? data.aws_eks_cluster.cluster[0].endpoint : ""
    cluster_ca_certificate = var.eks_ready ? base64decode(data.aws_eks_cluster.cluster[0].certificate_authority[0].data) : ""
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.cluster_name, "--region", var.aws_region]
    }
  }
}

provider "kubernetes" {
  host                   = var.eks_ready ? data.aws_eks_cluster.cluster[0].endpoint : ""
  cluster_ca_certificate = var.eks_ready ? base64decode(data.aws_eks_cluster.cluster[0].certificate_authority[0].data) : ""
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name, "--region", var.aws_region]
  }
}
