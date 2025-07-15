#!/bin/bash

# Script de deploy para a solução Memecoin Sniping MLOps

# Variáveis de ambiente (substitua pelos seus valores)
AWS_REGION="us-east-1"
S3_BUCKET_FOR_LAMBDA_CODE="your-lambda-code-s3-bucket"

# Obter Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

# Cria o bucket S3 para o código Lambda se não existir
aws s3 ls "s3://${S3_BUCKET_FOR_LAMBDA_CODE}" || aws s3 mb "s3://${S3_BUCKET_FOR_LAMBDA_CODE}"

# Deploy dos templates CloudFormation na ordem correta de dependência

echo "Deploying S3 stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/s3.yaml \
  --stack-name MemecoinSnipingS3 \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

# Obter o nome do bucket de artefatos de modelo do S3 stack output
OPTIMIZER_DATA_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name MemecoinSnipingS3 --query "Stacks[0].Outputs[?OutputKey==`ModelArtifactsBucketName`].OutputValue" --output text)

echo "Deploying SQS stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/sqs.yaml \
  --stack-name MemecoinSnipingSQS \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

echo "Deploying DynamoDB stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/dynamodb.yaml \
  --stack-name MemecoinSnipingDynamoDB \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

echo "Deploying Secrets Manager stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/secrets_manager.yaml \
  --stack-name MemecoinSnipingSecretsManager \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

echo "Deploying SNS stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/sns.yaml \
  --stack-name MemecoinSnipingSNS \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

echo "Deploying Lambda stack..."
# O deploy da stack Lambda deve vir antes do SageMaker para que o IAM Role seja criado
aws cloudformation deploy \
  --template-file iac/cloudformation/lambda.yaml \
  --stack-name MemecoinSnipingLambda \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    LambdaCodeS3BucketName=${S3_BUCKET_FOR_LAMBDA_CODE} \
    OptimizerDataBucketName=${OPTIMIZER_DATA_BUCKET_NAME} \
  --region ${AWS_REGION}

# Obter o ARN do IAM Role do SageMaker criado pela stack Lambda
SAGEMAKER_EXECUTION_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name MemecoinSnipingLambda --query "Stacks[0].Outputs[?OutputKey==`SageMakerExecutionRoleArn`].OutputValue" --output text)

echo "Deploying SageMaker stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/sagemaker.yaml \
  --stack-name MemecoinSnipingSageMaker \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    ModelArtifactsBucketName=${OPTIMIZER_DATA_BUCKET_NAME} \
    ExecutionRoleArn=${SAGEMAKER_EXECUTION_ROLE_ARN} \
  --region ${AWS_REGION}

echo "Deploying EventBridge stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/eventbridge.yaml \
  --stack-name MemecoinSnipingEventBridge \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

echo "Deploying Monitoring stack..."
aws cloudformation deploy \
  --template-file iac/cloudformation/monitoring.yaml \
  --stack-name MemecoinSnipingMonitoring \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

echo "Deployment complete!"


