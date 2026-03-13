"""Simple Bedrock runtime service for prompt -> text response."""

import os

import boto3
from botocore.exceptions import ClientError, BotoCoreError


class BedrockService:
    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    ):
        """Initialize the Bedrock runtime client."""
        model_id = os.getenv("BEDROCK_MODEL_ID", model_id)
        region = os.getenv("AWS_REGION", region)

        key_id = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        client_kwargs = {"service_name": "bedrock-runtime", "region_name": region}
        if key_id and secret_key:
            client_kwargs["aws_access_key_id"] = key_id
            client_kwargs["aws_secret_access_key"] = secret_key

        self._client = boto3.client(**client_kwargs)
        self._model_id = model_id

    def call_llm(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """Send a prompt to Bedrock and return the model response text."""

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        try:
            response = self._client.converse(
                modelId=self._model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                },
            )

            content = response["output"]["message"]["content"]

            text_parts = []
            for block in content:
                if "text" in block:
                    text_parts.append(block["text"])

            return "\n".join(text_parts).strip()

        except (ClientError, BotoCoreError) as e:
            raise RuntimeError(f"Bedrock request failed: {e}")
