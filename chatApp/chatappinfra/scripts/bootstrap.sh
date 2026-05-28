#!/usr/bin/env bash
# Creates the S3 bucket and DynamoDB table for Terraform remote state,
# then runs terraform init. Safe to re-run — all operations are idempotent.

set -euo pipefail

BUCKET="chatapp-remotestates3"
TABLE="chatapp-terraform-locks"
REGION="us-east-1"

echo "==> Checking S3 backend bucket: $BUCKET"
if aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null; then
  echo "    Bucket already exists, skipping."
else
  echo "    Creating bucket..."
  aws s3api create-bucket \
    --bucket "$BUCKET" \
    --region "$REGION"

  aws s3api put-bucket-versioning \
    --bucket "$BUCKET" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "$BUCKET" \
    --server-side-encryption-configuration '{
      "Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]
    }'

  aws s3api put-public-access-block \
    --bucket "$BUCKET" \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

  echo "    Bucket created and hardened."
fi

echo "==> Checking DynamoDB lock table: $TABLE"
if aws dynamodb describe-table --table-name "$TABLE" --region "$REGION" 2>/dev/null; then
  echo "    Table already exists, skipping."
else
  echo "    Creating table..."
  aws dynamodb create-table \
    --table-name "$TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION"

  aws dynamodb wait table-exists --table-name "$TABLE" --region "$REGION"
  echo "    Table created."
fi

echo "==> Running terraform init..."
terraform init \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=prod/terraform.tfstate" \
  -backend-config="region=$REGION" \
  -backend-config="dynamodb_table=$TABLE" \
  -backend-config="encrypt=true"

echo "==> Bootstrap complete."
