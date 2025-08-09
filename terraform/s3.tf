resource "random_id" "suffix" { byte_length = 4 }

resource "aws_s3_bucket" "ingest" {
  bucket = var.ingest_bucket_name
  tags = { Project = var.project_name, ManagedBy = "Terraform" }
}

resource "aws_s3_bucket_public_access_block" "ingest" {
  bucket = aws_s3_bucket.ingest.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "website" {
  bucket = var.website_bucket_name
  tags = { Project = var.project_name, ManagedBy = "Terraform" }
}

resource "aws_s3_bucket_ownership_controls" "website" {
  bucket = aws_s3_bucket.website.id
  rule { object_ownership = "BucketOwnerPreferred" }
}

# Mantener PRIVADO en el lab
resource "aws_s3_bucket_public_access_block" "website" {
  bucket = aws_s3_bucket.website.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "website" {
  bucket = aws_s3_bucket.website.id
  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

resource "aws_s3_bucket_cors_configuration" "website" {
  bucket = aws_s3_bucket.website.id
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}
