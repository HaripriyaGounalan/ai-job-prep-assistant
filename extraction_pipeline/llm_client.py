"""
Amazon Bedrock LLM client.

Wraps the Bedrock Runtime invoke_model API to send chat-style messages
and receive structured JSON responses. Includes retry logic and
response parsing.
"""

import json
import logging
import re
import time
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from config.settings import config

logger = logging.getLogger(__name__)


class BedrockLLMError(Exception):
    """Raised when a Bedrock invocation fails."""
    pass


class BedrockClient:
    """
    Client for Amazon Bedrock LLM invocations.

    Designed for structured extraction: sends a system+user message pair
    and expects a JSON object back. Handles Bedrock's Claude message
    format natively.
    """

    def __init__(self, bedrock_client=None):
        """
        Args:
            bedrock_client: Optional boto3 bedrock-runtime client for DI.
        """
        self.client = bedrock_client or boto3.client(
            "bedrock-runtime",
            region_name=config.aws.region,
        )
        self.model_id = config.bedrock.model_id
        self.max_tokens = config.bedrock.max_tokens
        self.temperature = config.bedrock.temperature
        self.max_retries = config.bedrock.max_retries

    def invoke_for_json(
        self,
        messages: list[dict],
        model_id: Optional[str] = None,
    ) -> dict:
        """
        Invoke Bedrock and parse the response as JSON.

        Args:
            messages: List of message dicts with 'role' and 'content'.
                      Must contain at least a system and user message.
            model_id: Override the default model ID.

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            BedrockLLMError: On invocation failure or invalid JSON response.
        """
        model = model_id or self.model_id

        # Separate system message from conversation messages
        system_messages = [m for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        # Build the Bedrock request body (Claude Messages API format)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": m["role"], "content": m["content"]}
                for m in conversation
            ],
        }

        if system_messages:
            body["system"] = system_messages[0]["content"]

        raw_response = self._invoke_with_retry(model, body)
        return self._parse_json_response(raw_response)

    def _invoke_with_retry(self, model_id: str, body: dict) -> str:
        """
        Call Bedrock with exponential-backoff retries.

        Returns:
            Raw text content from the LLM response.
        """
        last_error = None
        delay = 1.0

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body),
                )
                response_body = json.loads(response["body"].read())

                # Extract text from Claude's response format
                content = response_body.get("content", [])
                text_parts = [
                    block["text"]
                    for block in content
                    if block.get("type") == "text"
                ]
                if not text_parts:
                    raise BedrockLLMError("No text content in Bedrock response")

                return "\n".join(text_parts)

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                last_error = e
                # Retry on throttling or transient server errors
                if error_code in (
                    "ThrottlingException",
                    "ServiceUnavailableException",
                    "ModelTimeoutException",
                ):
                    logger.warning(
                        "Bedrock transient error (attempt %d/%d): %s",
                        attempt,
                        self.max_retries,
                        error_code,
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise BedrockLLMError(
                        f"Bedrock invocation failed: {e}"
                    ) from e
            except Exception as e:
                raise BedrockLLMError(
                    f"Unexpected error during Bedrock call: {e}"
                ) from e

        raise BedrockLLMError(
            f"Bedrock call failed after {self.max_retries} retries: {last_error}"
        )

    @staticmethod
    def _parse_json_response(raw_text: str) -> dict:
        """
        Parse JSON from LLM response text.

        Handles common LLM quirks:
          - JSON wrapped in markdown code fences
          - Leading/trailing whitespace
          - Text before or after the JSON object

        Returns:
            Parsed dict.

        Raises:
            BedrockLLMError: If no valid JSON can be extracted.
        """
        text = raw_text.strip()

        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find the outermost JSON object with brace matching
        start = text.find("{")
        if start != -1:
            depth = 0
            in_string = False
            escape_next = False
            for i in range(start, len(text)):
                ch = text[i]
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\":
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break

        raise BedrockLLMError(
            f"Could not extract valid JSON from LLM response. "
            f"Raw text (first 500 chars): {raw_text[:500]}"
        )