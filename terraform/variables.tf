variable "aws_region" {
  type        = string
  default     = "eu-west-1"
  description = "AWS region"
}

variable "project_name" {
  type        = string
  default     = "sentiment-analysis-aws"
}

variable "ingest_bucket_name" {
  type        = string
  default     = null
  description = "If null, it will be generated"
}

variable "website_bucket_name" {
  type        = string
  default     = null
  description = "If null, it will be generated"
}

variable "hf_api_token" {
  type        = string
  sensitive   = true
  description = "Hugging Face Inference API token (hf_...)"
}

variable "hf_model_id" {
  type        = string
  default     = "cardiffnlp/twitter-roberta-base-sentiment-latest"
  description = "HF model to call for sentiment"
}

variable "results_prefix" {
  type        = string
  default     = "results"
}

variable "csv_suffix" {
  type        = string
  default     = ".csv"
  description = "Only trigger Lambda when files with this suffix are uploaded"
}
