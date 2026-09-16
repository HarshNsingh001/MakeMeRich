# ---------------------------------------------------------
# S3 Object Storage
# ---------------------------------------------------------
resource "aws_s3_bucket" "datalake" {
  bucket = var.s3_bucket_name
}

resource "aws_s3_bucket_versioning" "datalake_versioning" {
  bucket = aws_s3_bucket.datalake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "datalake_lifecycle" {
  bucket = aws_s3_bucket.datalake.id

  rule {
    id     = "archive_old_data"
    status = "Enabled"
    
    filter {
      prefix = "raw_data_archive/"
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }
}
