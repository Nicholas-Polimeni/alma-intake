import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
import logging
from config import get_settings

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def get_s3_client():
    return boto3.client("s3")

async def upload_resume_to_s3(lead_id: str, resume: UploadFile) -> str:
    """
    Upload resume file to S3 and return the S3 key.
    
    Args:
        lead_id: Unique identifier for the lead
        resume: The uploaded file
        
    Returns:
        S3 key of the uploaded file
        
    Raises:
        Exception if upload fails
    """
    file_extension = resume.filename.split('.')[-1]
    s3_key = f"resumes/{lead_id}.{file_extension}"
    
    try:
        await resume.seek(0) # Reset file pointer
        file_content = await resume.read()
        
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=resume.content_type or 'application/pdf',
            Metadata={
                'original_filename': resume.filename,
                'lead_id': lead_id
            }
        )
        
        return s3_key
        
    except ClientError as e:
        raise Exception(f"Failed to upload resume: {str(e)}")


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """
    Generate a presigned URL for downloading a file from S3.
    
    Args:
        s3_key: The S3 key of the file
        expiration: URL expiration time in seconds (default: 1 hour)
        
    Returns:
        Presigned URL string
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise Exception(f"Failed to generate download URL: {str(e)}")