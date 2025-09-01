#!/usr/bin/env bash
set -euo pipefail

AWS_ENDPOINT="http://localhost:4566"
AWS="aws --endpoint-url=$AWS_ENDPOINT --region us-east-1"

TABLE_NAME="${DYNAMO_TABLE:-my-catalog-table}"
BUCKET="${S3_BUCKET:-catalog-bucket}"
QUEUE_NAME="${SQS_CATALOG_TOPIC:-catalog-emit.fifo}"

echo ">> aguardando LocalStack ficar pronto..."
until curl -s "$AWS_ENDPOINT/health" >/dev/null; do sleep 1; done
echo ">> LocalStack OK."

echo ">> criando DynamoDB table: $TABLE_NAME"
$AWS dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions AttributeName=ownerId,AttributeType=S AttributeName=sk,AttributeType=S \
  --key-schema AttributeName=ownerId,KeyType=HASH AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  >/dev/null 2>&1 || echo "   (já existe)"

echo ">> criando S3 bucket: $BUCKET"
$AWS s3api create-bucket --bucket "$BUCKET" \
  --create-bucket-configuration LocationConstraint=us-east-1 \
  >/dev/null 2>&1 || echo "   (já existe)"

echo ">> criando SQS FIFO queue: $QUEUE_NAME"
$AWS sqs create-queue \
  --queue-name "$QUEUE_NAME" \
  --attributes FifoQueue=true,ContentBasedDeduplication=false,VisibilityTimeout=30 \
  >/dev/null 2>&1 || echo "   (já existe)"

echo ">> recursos prontos."