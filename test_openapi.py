import pytest
import json
from adapters.openapi_adapter import OpenAPIAdapter, OpenAPIEndpoint


class TestOpenAPIAdapter:
    def test_import_simple_spec(self):
        adapter = OpenAPIAdapter()
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get all users",
                        "tags": ["users"],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        collections = adapter.import_from_dict(spec)
        
        assert len(collections) == 1
        assert collections[0]['name'] == 'users'
        assert len(collections[0]['requests']) == 1
        assert collections[0]['requests'][0]['method'] == 'GET'

    def test_import_with_params(self):
        adapter = OpenAPIAdapter()
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "parameters": [
                            {"name": "page", "in": "query", "schema": {"type": "integer", "example": 1}},
                            {"name": "Authorization", "in": "header", "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            }
        }
        
        collections = adapter.import_from_dict(spec)
        request = collections[0]['requests'][0]
        
        assert 'page' in request['params']
        assert 'Authorization' in request['headers']

    def test_import_with_body(self):
        adapter = OpenAPIAdapter()
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "example": {"name": "John", "email": "john@example.com"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }
        
        collections = adapter.import_from_dict(spec)
        request = collections[0]['requests'][0]
        
        assert request['body_type'] == 'JSON'
        assert 'John' in request['body']
        assert request['headers']['Content-Type'] == 'application/json'

    def test_export_simple_spec(self):
        adapter = OpenAPIAdapter()
        collections = [{
            'name': 'users',
            'is_folder': True,
            'requests': [{
                'name': 'Get Users',
                'method': 'GET',
                'url': '/api/users'
            }]
        }]
        
        spec = adapter.export_to_dict(collections, "Test API", "1.0.0")
        
        assert spec['openapi'] == '3.0.3'
        assert spec['info']['title'] == 'Test API'
        assert '/api/users' in spec['paths']
        assert 'get' in spec['paths']['/api/users']

    def test_export_with_body(self):
        adapter = OpenAPIAdapter()
        collections = [{
            'name': 'users',
            'requests': [{
                'name': 'Create User',
                'method': 'POST',
                'url': '/api/users',
                'body': '{"name": "Test"}',
                'body_type': 'JSON'
            }]
        }]
        
        spec = adapter.export_to_dict(collections)
        operation = spec['paths']['/api/users']['post']
        
        assert 'requestBody' in operation

    def test_validate_spec_valid(self):
        adapter = OpenAPIAdapter()
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}}
        }
        
        issues = adapter.validate_spec(spec)
        assert len(issues) == 0

    def test_validate_spec_missing_openapi(self):
        adapter = OpenAPIAdapter()
        spec = {
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {}
        }
        
        issues = adapter.validate_spec(spec)
        assert any("openapi" in issue.lower() for issue in issues)

    def test_validate_spec_missing_info(self):
        adapter = OpenAPIAdapter()
        spec = {
            "openapi": "3.0.3",
            "paths": {}
        }
        
        issues = adapter.validate_spec(spec)
        assert any("info" in issue.lower() for issue in issues)
