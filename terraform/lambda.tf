# Paquete zip creado por build.sh
locals {
  lambda_zip_path = "${path.module}/lambda_package/dist/function.zip"
}

resource "aws_lambda_function" "processor" {
  function_name = "${var.project_name}-processor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = local.lambda_zip_path
  timeout       = 120
  memory_size   = 512
  environment {
    variables = {
      INGEST_BUCKET     = aws_s3_bucket.ingest.id
      WEBSITE_BUCKET    = aws_s3_bucket.website.id
      RESULTS_PREFIX    = var.results_prefix
      HF_API_TOKEN      = var.hf_api_token
      HF_MODEL_ID       = var.hf_model_id
      CSV_SUFFIX        = var.csv_suffix
    }
  }
}

# Permitir a S3 invocar la lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.ingest.arn
}

# Notificación S3 → Lambda
resource "aws_s3_bucket_notification" "ingest_trigger" {
  bucket = aws_s3_bucket.ingest.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = var.csv_suffix
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
