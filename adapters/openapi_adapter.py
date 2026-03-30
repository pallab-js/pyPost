import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class OpenAPISpecInfo:
    title: str
    version: str
    description: Optional[str] = None
    contact: Optional[Dict] = None
    license: Optional[Dict] = None


@dataclass
class OpenAPIEndpoint:
    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = None
    parameters: List[Dict] = None
    request_body: Optional[Dict] = None
    responses: Dict = None
    deprecated: bool = False

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = []
        if self.responses is None:
            self.responses = {}


class OpenAPIAdapter:
    """Import/export OpenAPI 3.x specifications"""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager

    def import_from_dict(self, spec: Dict) -> List[Dict]:
        collections = []
        
        info = spec.get('info', {})
        servers = spec.get('servers', [{'url': ''}])
        base_url = servers[0].get('url', '') if servers else ''
        
        paths = spec.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                    continue
                
                endpoint = self._parse_operation(path, method, operation, base_url)
                
                collection_name = self._get_collection_name(endpoint.tags)
                collection = self._find_or_create_collection(collections, collection_name)
                
                request = self._operation_to_request(endpoint)
                collection['requests'].append(request)

        return collections

    def _parse_operation(self, path: str, method: str, operation: Dict, base_url: str) -> OpenAPIEndpoint:
        return OpenAPIEndpoint(
            path=path,
            method=method.upper(),
            operation_id=operation.get('operationId'),
            summary=operation.get('summary'),
            description=operation.get('description'),
            tags=operation.get('tags', []),
            parameters=operation.get('parameters', []),
            request_body=operation.get('requestBody'),
            responses=operation.get('responses', {}),
            deprecated=operation.get('deprecated', False)
        )

    def _get_collection_name(self, tags: List[str]) -> str:
        if tags:
            return tags[0]
        return 'Imported API'

    def _find_or_create_collection(self, collections: List[Dict], name: str) -> Dict:
        for collection in collections:
            if collection['name'] == name:
                return collection
        
        collection = {
            'name': name,
            'is_folder': True,
            'requests': []
        }
        collections.append(collection)
        return collection

    def _operation_to_request(self, endpoint: OpenAPIEndpoint) -> Dict:
        request = {
            'name': endpoint.summary or endpoint.operation_id or f"{endpoint.method} {endpoint.path}",
            'method': endpoint.method,
            'url': endpoint.path,
            'headers': {},
            'params': {},
            'body': None,
            'body_type': 'None',
            'description': endpoint.description or ''
        }

        for param in endpoint.parameters:
            param_name = param.get('name')
            param_in = param.get('in')
            param_required = param.get('required', False)
            param_schema = param.get('schema', {})
            example = param_schema.get('example', param_schema.get('default', ''))
            
            if param_in == 'query':
                request['params'][param_name] = str(example) if example else ''
            elif param_in == 'header':
                request['headers'][param_name] = str(example) if example else ''
            elif param_in == 'path':
                request['url'] = request['url'].replace(f'{{{param_name}}}', str(example) if example else param_name)

        if endpoint.request_body:
            content = endpoint.request_body.get('content', {})
            if 'application/json' in content:
                schema = content['application/json'].get('schema', {})
                example = content['application/json'].get('example')
                if not example:
                    example = self._generate_example_from_schema(schema)
                
                request['body'] = json.dumps(example, indent=2) if example else '{}'
                request['body_type'] = 'JSON'
                request['headers']['Content-Type'] = 'application/json'

        return request

    def _generate_example_from_schema(self, schema: Dict) -> Optional[Dict]:
        example = {}
        
        if schema.get('type') == 'object':
            properties = schema.get('properties', {})
            for prop_name, prop_schema in properties.items():
                example[prop_name] = self._get_example_value(prop_schema)
        elif schema.get('example'):
            return schema['example']
        
        return example if example else None

    def _get_example_value(self, schema: Dict) -> Any:
        if 'example' in schema:
            return schema['example']
        
        schema_type = schema.get('type', 'string')
        
        if schema_type == 'string':
            if schema.get('format') == 'email':
                return 'user@example.com'
            elif schema.get('format') == 'date':
                return '2024-01-01'
            elif schema.get('format') == 'date-time':
                return '2024-01-01T00:00:00Z'
            elif schema.get('format') == 'uuid':
                return '123e4567-e89b-12d3-a456-426614174000'
            elif schema.get('enum'):
                return schema['enum'][0]
            return f'{{example_{schema_type}}}'
        
        elif schema_type == 'integer' or schema_type == 'number':
            if 'minimum' in schema:
                return schema['minimum']
            return 0
        
        elif schema_type == 'boolean':
            return True
        
        elif schema_type == 'array':
            items = schema.get('items', {})
            return [self._get_example_value(items)]
        
        return None

    def import_from_file(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            return self.import_from_dict(spec)
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in OpenAPI file: {e}")
            return []

    def export_to_dict(self, collections: List[Dict], title: str = "API", version: str = "1.0.0") -> Dict:
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
                "description": "Generated by pyPost"
            },
            "paths": {}
        }

        for collection in collections:
            requests = collection.get('requests', [])
            if not requests:
                continue
            
            for request in requests:
                path, method = self._request_to_path_method(request)
                if not path or not method:
                    continue
                
                if path not in spec['paths']:
                    spec['paths'][path] = {}
                
                spec['paths'][path][method.lower()] = self._request_to_operation(request)

        return spec

    def _request_to_path_method(self, request: Dict) -> tuple:
        url = request.get('url', '')
        method = request.get('method', 'GET').upper()
        
        if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']:
            return None, None
        
        if url.startswith('/'):
            return url, method
        
        return f"/{url}", method

    def _request_to_operation(self, request: Dict) -> Dict:
        operation = {
            "summary": request.get('name', 'Unnamed Request'),
            "responses": {
                "200": {
                    "description": "Successful response"
                }
            }
        }

        if request.get('description'):
            operation['description'] = request['description']

        params = []
        request_params = request.get('params', {})
        for key, value in request_params.items():
            params.append({
                "name": key,
                "in": "query",
                "schema": {
                    "type": "string",
                    "example": value
                }
            })

        request_headers = request.get('headers', {})
        for key, value in request_headers.items():
            if key.lower() not in ['content-type', 'accept']:
                params.append({
                    "name": key,
                    "in": "header",
                    "schema": {
                        "type": "string",
                        "example": value
                    }
                })

        if params:
            operation['parameters'] = params

        body = request.get('body')
        body_type = request.get('body_type', 'None')
        
        if body and body_type == 'JSON':
            try:
                body_data = json.loads(body) if isinstance(body, str) else body
                operation['requestBody'] = {
                    "content": {
                        "application/json": {
                            "schema": self._generate_schema_from_example(body_data),
                            "example": body_data
                        }
                    }
                }
            except json.JSONDecodeError:
                pass

        return operation

    def _generate_schema_from_example(self, data: Any, depth: int = 0) -> Dict:
        if depth > 5:
            return {"type": "object"}
        
        if isinstance(data, dict):
            properties = {}
            for key, value in data.items():
                properties[key] = self._generate_schema_from_example(value, depth + 1)
            return {
                "type": "object",
                "properties": properties
            }
        elif isinstance(data, list) and data:
            return {
                "type": "array",
                "items": self._generate_schema_from_example(data[0], depth + 1)
            }
        elif isinstance(data, bool):
            return {"type": "boolean", "example": data}
        elif isinstance(data, int):
            return {"type": "integer", "example": data}
        elif isinstance(data, float):
            return {"type": "number", "example": data}
        else:
            return {"type": "string", "example": str(data)}

    def export_to_file(self, file_path: str, collections: List[Dict], title: str = "API", version: str = "1.0.0"):
        spec = self.export_to_dict(collections, title, version)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2)

    def validate_spec(self, spec: Dict) -> List[str]:
        issues = []
        
        if 'openapi' not in spec:
            issues.append("Missing 'openapi' version field")
        elif not spec['openapi'].startswith('3.'):
            issues.append(f"Unsupported OpenAPI version: {spec['openapi']}")
        
        if 'info' not in spec:
            issues.append("Missing 'info' object")
        else:
            info = spec['info']
            if 'title' not in info:
                issues.append("Missing 'info.title'")
            if 'version' not in info:
                issues.append("Missing 'info.version'")
        
        if 'paths' not in spec:
            issues.append("Missing 'paths' object")
        elif not spec['paths']:
            issues.append("No paths defined in specification")
        
        return issues
