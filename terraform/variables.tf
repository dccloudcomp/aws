variable "aws_region" {
  description = "Región AWS donde desplegar la infraestructura"
  type        = string
}

variable "project_name" {
  description = "Nombre base para los recursos"
  type        = string
}

variable "ingest_bucket_name" {
  description = "Nombre del bucket S3 para ingesta de CSV"
  type        = string
}

variable "website_bucket_name" {
  description = "Nombre del bucket S3 para el frontend y resultados"
  type        = string
}

variable "hf_api_token" {
  description = "Token de autenticación para Hugging Face API"
  type        = string
  sensitive   = true
}

variable "hf_model_id" {
  description = "ID del modelo en Hugging Face"
  type        = string
  default     = "cardiffnlp/twitter-roberta-base-sentiment-latest"
}

variable "results_prefix" {
  description = "Prefijo en el bucket website donde guardar resultados"
  type        = string
  default     = "results"
}

variable "csv_suffix" {
  description = "Sufijo de archivos CSV a procesar"
  type        = string
  default     = ".csv"
}

# ==== Variables para entorno sin permisos IAM ====
variable "manage_iam" {
  description = "Si es false, no crea roles ni políticas IAM y usa uno existente"
  type        = bool
  default     = false
}

variable "lambda_role_arn" {
  description = "ARN de un rol IAM existente para la Lambda (si manage_iam=false)"
  type        = string
}

variable "frontend_bucket_name" {
  type        = string
  description = "Nombre único para el bucket del frontend"
}
