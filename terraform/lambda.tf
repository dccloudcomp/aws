# Ruta al ZIP generado por lambda_package/build.sh
# Estructura asumida:
#   terraform/
#     lambda_package/dist/function.zip
locals {
  lambda_zip_path = "${path.module}/lambda_package/dist/function.zip"
}

resource "aws_lambda_function" "processor" {
  function_name = "${var.project_name}-processor"

  filename         = local.lambda_zip_path
  source_code_hash = filebase64sha256(local.lambda_zip_path)

  handler = "main.handler"
  runtime = "python3.11"
  timeout = 60
  memory_size = 512
  architectures = ["x86_64"]

  # Si manage_iam=false => usa un rol EXISTENTE pasado por variable
  role = var.manage_iam ? aws_iam_role.lambda_role[0].arn : var.lambda_role_arn

  environment {
    variables = {
      HF_API_TOKEN   = var.hf_api_token
      HF_MODEL_ID    = var.hf_model_id
      INGEST_BUCKET  = var.ingest_bucket_name
      WEBSITE_BUCKET = var.website_bucket_name
      RESULTS_PREFIX = var.results_prefix
      CSV_SUFFIX     = var.csv_suffix
    }
  }

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

# Permite que S3 (bucket ingest) invoque la Lambda cuando se suba un .csv
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.ingest_bucket_name}"
}

# Notificación del bucket de ingesta -> invoca la Lambda en ObjectCreated con filtro por sufijo csv
resource "aws_s3_bucket_notification" "ingest_trigger" {
  bucket = var.ingest_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = var.csv_suffix
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
