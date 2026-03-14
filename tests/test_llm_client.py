"""Tests for the Bedrock LLM client."""

import json
import pytest
from unittest.mock import MagicMock, patch

from extraction_pipeline.llm_client import BedrockClient, BedrockLLMError


class TestJsonParsing:
    """Test the _parse_json_response static method with various LLM outputs."""

    def test_clean_json(self):
        raw = '{"name": "test", "skills": ["Python", "Go"]}'
        result = BedrockClient._parse_json_response(raw)
        assert result["name"] == "test"
        assert result["skills"] == ["Python", "Go"]

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"name": "test"}\n```'
        result = BedrockClient._parse_json_response(raw)
        assert result["name"] == "test"

    def test_json_with_plain_fences(self):
        raw = '```\n{"value": 42}\n```'
        result = BedrockClient._parse_json_response(raw)
        assert result["value"] == 42

    def test_json_with_preamble(self):
        raw = 'Here is the extracted data:\n\n{"job_title": "Engineer"}'
        result = BedrockClient._parse_json_response(raw)
        assert result["job_title"] == "Engineer"

    def test_json_with_trailing_text(self):
        raw = '{"job_title": "Engineer"}\n\nI hope this helps!'
        result = BedrockClient._parse_json_response(raw)
        assert result["job_title"] == "Engineer"

    def test_nested_json(self):
        raw = json.dumps({
            "name": "Jane",
            "experience": [
                {"title": "SWE", "highlights": ["Built APIs"]},
            ],
        })
        result = BedrockClient._parse_json_response(raw)
        assert result["experience"][0]["title"] == "SWE"

    def test_json_with_escaped_quotes(self):
        raw = '{"summary": "She said \\"hello\\" to the team"}'
        result = BedrockClient._parse_json_response(raw)
        assert "hello" in result["summary"]

    def test_invalid_json_raises_error(self):
        raw = "This is not JSON at all"
        with pytest.raises(BedrockLLMError, match="Could not extract valid JSON"):
            BedrockClient._parse_json_response(raw)

    def test_empty_string_raises_error(self):
        with pytest.raises(BedrockLLMError):
            BedrockClient._parse_json_response("")

    def test_whitespace_around_json(self):
        raw = "   \n\n  {\"key\": \"value\"}  \n\n  "
        result = BedrockClient._parse_json_response(raw)
        assert result["key"] == "value"


class TestInvokeForJson:
    """Test the full invoke_for_json flow with a mocked boto3 client."""

    def _make_bedrock_response(self, text: str) -> dict:
        """Build a mock Bedrock invoke_model response."""
        body_content = json.dumps({
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
        }).encode()

        mock_body = MagicMock()
        mock_body.read.return_value = body_content
        return {"body": mock_body}

    def test_successful_invocation(self):
        response_json = {"job_title": "Engineer", "required_skills": ["Python"]}
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = self._make_bedrock_response(
            json.dumps(response_json)
        )

        client = BedrockClient(bedrock_client=mock_client)
        result = client.invoke_for_json([
            {"role": "system", "content": "You are a parser."},
            {"role": "user", "content": "Parse this JD."},
        ])

        assert result["job_title"] == "Engineer"
        assert result["required_skills"] == ["Python"]

        # Verify the call was made correctly
        call_args = mock_client.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        assert "system" in body
        assert body["messages"][0]["role"] == "user"

    def test_retry_on_throttle(self):
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        # First call throttled, second succeeds
        mock_client.invoke_model.side_effect = [
            ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
                "InvokeModel",
            ),
            self._make_bedrock_response('{"result": "ok"}'),
        ]

        client = BedrockClient(bedrock_client=mock_client)
        result = client.invoke_for_json([
            {"role": "user", "content": "test"},
        ])

        assert result["result"] == "ok"
        assert mock_client.invoke_model.call_count == 2

    def test_non_retryable_error_raises(self):
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "bad request"}},
            "InvokeModel",
        )

        client = BedrockClient(bedrock_client=mock_client)
        with pytest.raises(BedrockLLMError, match="invocation failed"):
            client.invoke_for_json([{"role": "user", "content": "test"}])

    def test_empty_response_raises(self):
        body_content = json.dumps({
            "content": [],
            "stop_reason": "end_turn",
        }).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = body_content

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": mock_body}

        client = BedrockClient(bedrock_client=mock_client)
        with pytest.raises(BedrockLLMError, match="No text content"):
            client.invoke_for_json([{"role": "user", "content": "test"}])