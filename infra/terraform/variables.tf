variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "db_name" {
  type    = string
  default = "makemerich"
}

variable "db_username" {
  type    = string
  default = "admin"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "s3_bucket_name" {
  type    = string
  default = "makemerich-datalake-prod"
}

variable "docker_image" {
  type        = string
  description = "ECR image URL for the API backend"
  default     = "nginx:latest" # Placeholder for testing
}
