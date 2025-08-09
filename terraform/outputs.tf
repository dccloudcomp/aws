output "ingest_bucket" {
  description = "Nombre del bucket S3 de ingesta (donde subir CSV)"
  value       = aws_s3_bucket.ingest.bucket
}

output "website_bucket" {
  description = "Nombre del bucket S3 para el frontend y resultados"
  value       = aws_s3_bucket.website.bucket
}

output "website_url" {
  description = "Endpoint del website S3"
  value       = aws_s3_bucket_website_configuration.website.website_endpoint
}

output "lambda_name" {
  description = "Nombre de la función Lambda de procesamiento"
  value       = aws_lambda_function.processor.function_name
}
