"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and type safety.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AWSConfig:
    """AWS service configuration."""
    region: str = os.getenv("AWS_REGION", "us-east-1")
    access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")


@dataclass
class S3Config:
    """S3 bucket and prefix configuration."""
    bucket_name: str = os.getenv("S3_BUCKET_NAME", "job-prep-assistant-files")
    resume_prefix: str = os.getenv("S3_RESUME_PREFIX", "uploads/resumes/")
    job_desc_prefix: str = os.getenv("S3_JOB_DESC_PREFIX", "uploads/job-descriptions/")
    processed_prefix: str = os.getenv("S3_PROCESSED_PREFIX", "processed/")


@dataclass
class TextractConfig:
    """AWS Textract configuration."""
    max_retries: int = int(os.getenv("TEXTRACT_MAX_RETRIES", "3"))
    retry_delay: int = int(os.getenv("TEXTRACT_RETRY_DELAY", "2"))


@dataclass
class ProcessingConfig:
    """File processing constraints."""
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    allowed_extensions: list[str] = field(default_factory=lambda: (
        os.getenv("ALLOWED_EXTENSIONS", ".pdf,.png,.jpg,.jpeg,.tiff").split(",")
    ))

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@dataclass
class BedrockConfig:
    """Amazon Bedrock LLM configuration."""
    model_id: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )
    max_tokens: int = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))
    temperature: float = float(os.getenv("BEDROCK_TEMPERATURE", "0.0"))
    # Retry configuration for transient Bedrock errors
    max_retries: int = int(os.getenv("BEDROCK_MAX_RETRIES", "3"))


@dataclass
class AppConfig:
    """Root application configuration."""
    aws: AWSConfig = field(default_factory=AWSConfig)
    s3: S3Config = field(default_factory=S3Config)
    textract: TextractConfig = field(default_factory=TextractConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    bedrock: BedrockConfig = field(default_factory=BedrockConfig)


# Singleton config instance
config = AppConfig()