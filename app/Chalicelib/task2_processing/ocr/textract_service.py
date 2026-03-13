"""
TextractService class to handle text extraction from images using AWS Textract.
This is a wrapper around AWS Textract to provide a consistent interface for text extraction.
"""

import boto3
import time

class TextractService:
    """
    Provides text extraction via AWS Textract.
    Returns a list of lines with their text and confidence.
    """

    def __init__(self, storage_location: str,  region: str = "us-east-1"):
        """Create a boto3 client for the Textract service."""
        self._client = boto3.client("textract", region_name=region)
        self._storage_location = storage_location

    def detect_text(self, file_key):

        if file_key.lower().endswith(".pdf"):
            job = self._client.start_document_text_detection(
                DocumentLocation={"S3Object": {"Bucket": self._storage_location, "Name": file_key}}
            )
            job_id = job["JobId"]

            while True:
                result = self._client.get_document_text_detection(JobId=job_id)
                if result["JobStatus"] == "SUCCEEDED":
                    blocks = result["Blocks"]
                    break
                time.sleep(1)
        else:
            result = self._client.detect_document_text(
                Document={"S3Object": {"Bucket": self._storage_location, "Name": file_key}}
            )
            blocks = result["Blocks"]

        lines = []
        for b in blocks:
            if b["BlockType"] == "LINE":
                lines.append({"text": b["Text"], "confidence": b["Confidence"]})

        return lines