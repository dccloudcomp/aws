# Documentos de políticas (no crean recursos por sí solos)

# Trust policy para que Lambda asuma el rol (solo se usa si manage_iam=true)
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Policy mínima para Lambda: leer CSV del bucket ingest, escribir resultados en website, y logs
data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid    = "S3ReadIngest"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      "arn:aws:s3:::${var.ingest_bucket_name}",
      "arn:aws:s3:::${var.ingest_bucket_name}/*",
    ]
  }

  statement {
    sid    = "S3WriteWebsite"
    effect = "Allow"
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "arn:aws:s3:::${var.website_bucket_name}/${var.results_prefix}/*",
    ]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }
}

# ====== Recursos IAM (solo se crean si manage_iam=true) ======

resource "aws_iam_role" "lambda_role" {
  count              = var.manage_iam ? 1 : 0
  name               = "${var.project_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

resource "aws_iam_policy" "lambda_policy" {
  count       = var.manage_iam ? 1 : 0
  name        = "${var.project_name}-lambda-policy"
  description = "Permisos mínimos para Lambda (S3 ingest read, S3 website write, logs)"
  policy      = data.aws_iam_policy_document.lambda_policy.json
  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  count      = var.manage_iam ? 1 : 0
  role       = aws_iam_role.lambda_role[0].name
  policy_arn = aws_iam_policy.lambda_policy[0].arn
}
