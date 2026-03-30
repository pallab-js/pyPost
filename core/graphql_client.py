import json
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class GraphQLRequest:
    query: str
    variables: Optional[Dict[str, Any]] = None
    operation_name: Optional[str] = None


@dataclass
class GraphQLResponse:
    data: Optional[Any] = None
    errors: Optional[list] = None
    extensions: Optional[Dict] = None

    @property
    def is_error(self) -> bool:
        return self.errors is not None and len(self.errors) > 0


class GraphQLClient:
    """Client for GraphQL requests"""

    @staticmethod
    def build_request_body(request: GraphQLRequest) -> Dict:
        body = {'query': request.query}
        if request.variables:
            body['variables'] = request.variables
        if request.operation_name:
            body['operationName'] = request.operation_name
        return body

    @staticmethod
    def parse_response(response_text: str) -> GraphQLResponse:
        try:
            data = json.loads(response_text)
            return GraphQLResponse(
                data=data.get('data'),
                errors=data.get('errors'),
                extensions=data.get('extensions')
            )
        except json.JSONDecodeError:
            return GraphQLResponse(errors=[{'message': 'Invalid JSON response'}])

    @staticmethod
    def validate_query(query: str) -> tuple[bool, Optional[str]]:
        if not query or not query.strip():
            return False, "Query cannot be empty"
        stripped = query.strip()
        if not (stripped.startswith('{') or 
                'query' in stripped or 
                'mutation' in stripped or 
                'subscription' in stripped):
            return False, "Query must contain query, mutation, subscription, or start with '{'"
        return True, None

    @staticmethod
    def validate_variables(variables_text: str) -> tuple[bool, Optional[Dict], Optional[str]]:
        if not variables_text.strip():
            return True, None, None
        try:
            variables = json.loads(variables_text)
            if not isinstance(variables, dict):
                return False, None, "Variables must be a JSON object"
            return True, variables, None
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON in variables: {str(e)}"
