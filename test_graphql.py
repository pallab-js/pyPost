import pytest
import json
from core.graphql_client import GraphQLClient, GraphQLRequest, GraphQLResponse


class TestGraphQLClient:
    def test_build_request_body_query_only(self):
        req = GraphQLRequest(query="{ users { id } }")
        body = GraphQLClient.build_request_body(req)
        assert body == {"query": "{ users { id } }"}

    def test_build_request_body_with_variables(self):
        req = GraphQLRequest(
            query="query($id: ID!) { user(id: $id) { name } }",
            variables={"id": "123"}
        )
        body = GraphQLClient.build_request_body(req)
        assert body == {
            "query": "query($id: ID!) { user(id: $id) { name } }",
            "variables": {"id": "123"}
        }

    def test_build_request_body_with_operation_name(self):
        req = GraphQLRequest(
            query="query UserQuery { user { name } }",
            operation_name="UserQuery"
        )
        body = GraphQLClient.build_request_body(req)
        assert body["operationName"] == "UserQuery"

    def test_parse_response_success(self):
        response_text = '{"data": {"users": [{"id": 1}]}}'
        response = GraphQLClient.parse_response(response_text)
        assert response.data == {"users": [{"id": 1}]}
        assert response.errors is None
        assert not response.is_error

    def test_parse_response_with_errors(self):
        response_text = '{"data": null, "errors": [{"message": "Not found"}]}'
        response = GraphQLClient.parse_response(response_text)
        assert response.data is None
        assert len(response.errors) == 1
        assert response.is_error

    def test_parse_invalid_json(self):
        response_text = "not json"
        response = GraphQLClient.parse_response(response_text)
        assert response.errors is not None
        assert response.is_error

    def test_validate_query_valid(self):
        valid, error = GraphQLClient.validate_query("{ users { id } }")
        assert valid is True
        assert error is None

    def test_validate_query_empty(self):
        valid, error = GraphQLClient.validate_query("")
        assert valid is False
        assert "empty" in error.lower()

    def test_validate_query_no_keyword(self):
        valid, error = GraphQLClient.validate_query("{ users { id } }")
        assert valid is True

    def test_validate_variables_valid_json(self):
        valid, variables, error = GraphQLClient.validate_variables('{"id": 1}')
        assert valid is True
        assert variables == {"id": 1}
        assert error is None

    def test_validate_variables_empty(self):
        valid, variables, error = GraphQLClient.validate_variables("")
        assert valid is True
        assert variables is None

    def test_validate_variables_invalid_json(self):
        valid, variables, error = GraphQLClient.validate_variables("{ invalid }")
        assert valid is False
        assert variables is None
        assert "Invalid JSON" in error
