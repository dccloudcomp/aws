output "ingest_bucket" {
  value = aws_s3_bucket.ingest.id
}

output "website_bucket" {
  value = aws_s3_bucket.website.id
}

output "website_url" {
  value       = aws_s3_bucket_website_configuration.website.website_endpoint
  description = "S3 static website endpoint (HTTP)"
}

output "lambda_name" {
  value = aws_lambda_function.processor.function_name
}
