import json
import logging
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import ClientError
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class S3StorageClient:
    """Client for interacting with AWS S3 Object Storage."""
    
    def __init__(self):
        self.bucket = settings.s3_bucket_name
        self.enabled = bool(
            self.bucket and 
            settings.aws_access_key_id and 
            settings.aws_secret_access_key
        )
        
        if self.enabled:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                logger.info(f"S3StorageClient initialized for bucket: {self.bucket}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self.enabled = False
        else:
            logger.warning("S3 Storage is disabled. Missing AWS credentials or bucket name in config.")

    def upload_json(self, object_key: str, data: Dict[str, Any]) -> bool:
        """Uploads a dictionary as a JSON object to S3."""
        if not self.enabled:
            logger.debug(f"[DISABLED] Would have uploaded {object_key} to S3.")
            return False
            
        try:
            json_str = json.dumps(data)
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=json_str,
                ContentType='application/json'
            )
            logger.info(f"Successfully uploaded {object_key} to S3 bucket {self.bucket}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload {object_key} to S3: {e}")
            return False

    def download_json(self, object_key: str) -> Optional[Dict[str, Any]]:
        """Downloads and parses a JSON object from S3."""
        if not self.enabled:
            return None
            
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=object_key
            )
            body = response['Body'].read().decode('utf-8')
            return json.loads(body)
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                logger.warning(f"S3 object {object_key} does not exist.")
            else:
                logger.error(f"Failed to download {object_key} from S3: {e}")
            return None

storage_client = S3StorageClient()
