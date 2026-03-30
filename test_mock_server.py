import pytest
from engine.mock_server import MockServer, MockEndpoint


class TestMockEndpoint:
    def test_matches_exact(self):
        endpoint = MockEndpoint(
            path='/api/users',
            method='GET',
            response_data={'users': []}
        )
        assert endpoint.matches('/api/users', 'GET') is True
        assert endpoint.matches('/api/users', 'POST') is False
        assert endpoint.matches('/api/other', 'GET') is False

    def test_matches_case_insensitive(self):
        endpoint = MockEndpoint(
            path='/api/test',
            method='get',
            response_data={}
        )
        assert endpoint.matches('/api/test', 'GET') is True
        assert endpoint.matches('/api/test', 'Get') is True


class TestMockServer:
    def test_add_endpoint(self):
        server = MockServer(port=5555)
        endpoint = MockEndpoint(
            path='/test',
            method='GET',
            response_data={'status': 'ok'}
        )
        server.add_endpoint(endpoint)
        assert len(server.endpoints) == 1

    def test_remove_endpoint(self):
        server = MockServer(port=5556)
        endpoint = MockEndpoint(
            path='/test',
            method='GET',
            response_data={}
        )
        server.add_endpoint(endpoint)
        assert server.remove_endpoint('/test', 'GET') is True
        assert len(server.endpoints) == 0

    def test_get_endpoint(self):
        server = MockServer(port=5557)
        endpoint = MockEndpoint(
            path='/api/users',
            method='GET',
            response_data={'users': []}
        )
        server.add_endpoint(endpoint)
        
        result = server.get_endpoint('/api/users', 'GET')
        assert result is not None
        assert result.path == '/api/users'
        
        missing = server.get_endpoint('/api/missing', 'GET')
        assert missing is None

    def test_list_endpoints(self):
        server = MockServer(port=5558)
        server.add_endpoint(MockEndpoint('/a', 'GET', {}))
        server.add_endpoint(MockEndpoint('/b', 'POST', {}))
        
        endpoints = server.list_endpoints()
        assert len(endpoints) == 2

    def test_export_import_json(self):
        server = MockServer(port=5559)
        server.add_endpoint(MockEndpoint(
            path='/api/users',
            method='GET',
            response_data={'id': 1, 'name': 'Test'},
            status_code=200
        ))
        
        json_str = server.export_to_json()
        assert '/api/users' in json_str
        assert 'GET' in json_str

    def test_add_from_dict(self):
        server = MockServer(port=5560)
        data = {
            'path': '/api/test',
            'method': 'POST',
            'response': {'created': True},
            'status_code': 201
        }
        result = server.add_from_dict(data)
        assert result is True
        assert len(server.endpoints) == 1
        assert server.endpoints[0].status_code == 201

    def test_get_url(self):
        server = MockServer(host='localhost', port=8080)
        assert server.get_url() == 'http://localhost:8080'

    def test_create_example_endpoints(self):
        endpoints = MockServer.create_example_endpoints()
        assert len(endpoints) > 0
        assert any(ep.path == '/api/users' for ep in endpoints)
