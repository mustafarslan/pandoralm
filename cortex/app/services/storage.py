
import boto3
from app.core.config import settings

class StorageService:
    def __init__(self):
        kwargs = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.S3_REGION_NAME,
        }
        if settings.AWS_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL

        self.s3_client = boto3.client("s3", **kwargs)

    def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL to share an S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            return ""

    def list_objects(self, bucket: str, prefix: str) -> list:
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return response.get('Contents', [])
        except Exception as e:
            print(f"Error listing objects: {e}")
            return []

_storage_service = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
