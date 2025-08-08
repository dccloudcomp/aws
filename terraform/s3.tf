locals {
  ingest_bucket_name  = coalesce(var.ingest_bucket_name, "${var.project_name}-ingest-${random_id.suffix.hex}")
  website_bucket_name = coalesce(var.website_bucket_name, "${var.project_name}-website-${random_id.suffix.hex}")
}

resource "random_id" "suffix" {
  byte_length = 4
}

# Bucket de ingesta (privado)
resource "aws_s3_bucket" "ingest" {
  bucket = local.ingest_bucket_name
  force_destroy = true
  tags = {
    Project = var.project_name
    Purpose = "ingest"
  }
}

resource "aws_s3_bucket_public_access_block" "ingest" {
  bucket                  = aws_s3_bucket.ingest.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket del frontend + resultados (público para lectura)
resource "aws_s3_bucket" "website" {
  bucket        = local.website_bucket_name
  force_destroy = true
  tags = {
    Project = var.project_name
    Purpose = "website"
  }
}

resource "aws_s3_bucket_website_configuration" "website" {
  bucket = aws_s3_bucket.website.id
  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_ownership_controls" "website" {
  bucket = aws_s3_bucket.website.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "website" {
  bucket                  = aws_s3_bucket.website.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Política pública de lectura de objetos
data "aws_iam_policy_document" "website_public_read" {
  statement {
    sid     = "PublicReadGetObject"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    resources = [
      "${aws_s3_bucket.website.arn}/*"
    ]
  }
}

resource "aws_s3_bucket_policy" "website" {
  bucket = aws_s3_bucket.website.id
  policy = data.aws_iam_policy_document.website_public_read.json
}

# CORS para permitir que el frontend lea JSON/CSV
resource "aws_s3_bucket_cors_configuration" "website" {
  bucket = aws_s3_bucket.website.id
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
