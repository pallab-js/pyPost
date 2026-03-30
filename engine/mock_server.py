import json
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading


@dataclass
class MockEndpoint:
    path: str
    method: str
    response_data: Dict
    status_code: int = 200
    delay_ms: int = 0
    headers: Dict = field(default_factory=dict)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def matches(self, path: str, method: str) -> bool:
        return self.path == path and self.method.upper() == method.upper()


class MockServer:
    """Local mock server for API testing with static responses"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.endpoints: List[MockEndpoint] = []
        self.server_thread: Optional[threading.Thread] = None
        self._running = False
        self._app = None
        self._request_log: List[Dict] = []
        logging.info(f"MockServer initialized on {host}:{port}")
    
    def add_endpoint(self, endpoint: MockEndpoint):
        self.endpoints.append(endpoint)
        logging.info(f"Added endpoint: {endpoint.method} {endpoint.path}")
    
    def remove_endpoint(self, path: str, method: str) -> bool:
        for i, ep in enumerate(self.endpoints):
            if ep.matches(path, method):
                self.endpoints.pop(i)
                logging.info(f"Removed endpoint: {method} {path}")
                return True
        return False
    
    def clear_endpoints(self):
        self.endpoints.clear()
        logging.info("Cleared all endpoints")
    
    def get_endpoint(self, path: str, method: str) -> Optional[MockEndpoint]:
        for ep in self.endpoints:
            if ep.matches(path, method):
                return ep
        return None
    
    def list_endpoints(self) -> List[Dict]:
        return [
            {
                'path': ep.path,
                'method': ep.method,
                'status_code': ep.status_code,
                'description': ep.description,
                'tags': ep.tags,
                'has_delay': ep.delay_ms > 0
            }
            for ep in self.endpoints
        ]
    
    def add_from_dict(self, data: Dict) -> bool:
        try:
            endpoint = MockEndpoint(
                path=data['path'],
                method=data['method'],
                response_data=data['response'],
                status_code=data.get('status_code', 200),
                delay_ms=data.get('delay_ms', 0),
                headers=data.get('headers', {}),
                description=data.get('description', ''),
                tags=data.get('tags', [])
            )
            self.add_endpoint(endpoint)
            return True
        except KeyError as e:
            logging.error(f"Invalid endpoint data: missing {e}")
            return False
    
    def import_from_json(self, json_str: str) -> int:
        try:
            data = json.loads(json_str)
            return self.import_from_list(data)
        except json.JSONDecodeError:
            logging.error("Invalid JSON for import")
            return 0
    
    def import_from_list(self, data: List[Dict]) -> int:
        count = 0
        for item in data:
            if self.add_from_dict(item):
                count += 1
        return count
    
    def export_to_list(self) -> List[Dict]:
        return [
            {
                'path': ep.path,
                'method': ep.method,
                'response': ep.response_data,
                'status_code': ep.status_code,
                'delay_ms': ep.delay_ms,
                'headers': ep.headers,
                'description': ep.description,
                'tags': ep.tags
            }
            for ep in self.endpoints
        ]
    
    def export_to_json(self) -> str:
        return json.dumps(self.export_to_list(), indent=2)
    
    def start(self) -> bool:
        if self._running:
            logging.warning("Mock server already running")
            return False
        
        try:
            from flask import Flask, request, jsonify, Response
            
            self._app = Flask(__name__)
            
            @self._app.route('/<path:subpath>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
            def handle_subpath(subpath):
                return self._handle_request(f'/{subpath}', request)
            
            @self._app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
            @self._app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
            def handle_root(path=''):
                return self._handle_request(f'/{path}' if path else '/', request)
            
            self._running = True
            self.server_thread = threading.Thread(target=self._run, daemon=True)
            self.server_thread.start()
            logging.info(f"Mock server started on {self.host}:{self.port}")
            return True
            
        except ImportError:
            logging.error("Flask not installed. Run: pip install flask")
            return False
        except Exception as e:
            logging.error(f"Failed to start mock server: {e}")
            return False
    
    def _run(self):
        try:
            self._app.run(host=self.host, port=self.port, threaded=True, use_reloader=False)
        except Exception as e:
            logging.error(f"Mock server error: {e}")
            self._running = False
    
    def _handle_request(self, path: str, flask_request):
        from flask import jsonify
        
        method = flask_request.method
        endpoint = self.get_endpoint(path, method)
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'path': path,
            'method': method,
            'matched': endpoint is not None,
            'status_code': 404 if not endpoint else endpoint.status_code
        }
        self._request_log.append(log_entry)
        
        if not endpoint:
            return jsonify({
                'error': 'Not Found',
                'message': f'No mock endpoint defined for {method} {path}',
                'available_endpoints': self.list_endpoints()
            }), 404
        
        if endpoint.delay_ms > 0:
            time.sleep(endpoint.delay_ms / 1000)
        
        log_entry['delay_applied'] = endpoint.delay_ms
        
        headers = {'Content-Type': 'application/json'}
        headers.update(endpoint.headers)
        
        response_headers = [(k, v) for k, v in headers.items()]
        
        return Response(
            json.dumps(endpoint.response_data),
            status=endpoint.status_code,
            headers=response_headers,
            mimetype='application/json'
        )
    
    def stop(self):
        self._running = False
        logging.info("Mock server stopped")
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def get_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    def get_request_log(self) -> List[Dict]:
        return self._request_log.copy()
    
    def clear_request_log(self):
        self._request_log.clear()
    
    @staticmethod
    def create_example_endpoints() -> List[MockEndpoint]:
        return [
            MockEndpoint(
                path='/api/users',
                method='GET',
                response_data={
                    'users': [
                        {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
                        {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com'}
                    ]
                },
                description='Get all users',
                tags=['users']
            ),
            MockEndpoint(
                path='/api/users/1',
                method='GET',
                response_data={'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
                description='Get user by ID',
                tags=['users']
            ),
            MockEndpoint(
                path='/api/users',
                method='POST',
                response_data={'id': 3, 'name': 'New User', 'email': 'new@example.com'},
                status_code=201,
                description='Create new user',
                tags=['users']
            ),
            MockEndpoint(
                path='/api/users/1',
                method='PUT',
                response_data={'id': 1, 'name': 'Updated User', 'email': 'updated@example.com'},
                description='Update user',
                tags=['users']
            ),
            MockEndpoint(
                path='/api/users/1',
                method='DELETE',
                response_data={'message': 'User deleted'},
                status_code=204,
                description='Delete user',
                tags=['users']
            ),
            MockEndpoint(
                path='/api/slow',
                method='GET',
                response_data={'message': 'This is a slow response'},
                delay_ms=2000,
                description='Slow endpoint for testing timeouts',
                tags=['testing']
            ),
            MockEndpoint(
                path='/api/error',
                method='GET',
                response_data={'error': 'Internal Server Error'},
                status_code=500,
                description='Simulated server error',
                tags=['testing']
            ),
        ]
