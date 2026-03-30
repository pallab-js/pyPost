import time
import os
import requests
import logging
from typing import Dict, Optional
from PySide6.QtCore import QThread, Signal
from constants import MAX_RESPONSE_SIZE_DISPLAY, MAX_RESPONSE_SIZE_LOG, RESPONSE_TRUNCATION_MESSAGE


class HTTPWorker(QThread):
    """Worker thread for HTTP requests to keep UI responsive"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, method: str, url: str, headers: Dict, data: Optional[str] = None, 
                 params: Optional[Dict] = None, verify: bool = True, files: Optional[Dict] = None, 
                 db_manager=None, use_cache: bool = False, timeout: int = 30,
                 max_retries: int = 3, pool_connections: int = 10, pool_maxsize: int = 20):
        super().__init__()
        self.method = method
        self.url = url
        self.headers = headers
        self.data = data
        self.params = params
        self.verify = verify
        self.files = files
        self.db_manager = db_manager
        self.use_cache = use_cache
        self.timeout = timeout
        self.max_retries = max_retries
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self._should_stop = False
        self._session = None
        self._opened_files: list = []

    def cancel(self):
        """Cancel the ongoing request"""
        self._should_stop = True

    def _cleanup_files(self):
        """Clean up opened file handles"""
        for file_obj in self._opened_files:
            try:
                if hasattr(file_obj, 'close'):
                    file_obj.close()
            except Exception:
                pass
        self._opened_files.clear()

    def _create_session(self) -> requests.Session:
        """Create a configured requests session with connection pooling"""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            max_retries=self.max_retries
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def run(self):
        import json as json_module
        try:
            if self._should_stop:
                return

            logging.info(f"Sending {self.method} request to {self.url}")

            if self.use_cache and self.db_manager and self.method.upper() == 'GET':
                cache_key = self.db_manager.get_cache_key(self.method, self.url, self.headers, self.data)
                cached_response = self.db_manager.get_cached_response(cache_key)
                if cached_response:
                    logging.info("Returning cached response")
                    result = {
                        'status_code': cached_response['status_code'],
                        'headers': json_module.loads(cached_response['headers']) if cached_response['headers'] else {},
                        'cookies': {},
                        'text': cached_response['response_data'],
                        'response_time': 0,
                        'size': len(cached_response['response_data'].encode()),
                        'cached': True
                    }
                    self.finished.emit(result)
                    return
            
            processed_files = self._prepare_files()

            if self._should_stop:
                self._cleanup_files()
                return

            start_time = time.time()
            self._session = self._create_session()
            
            if self._should_stop:
                self._cleanup_files()
                return
            
            response = self._session.request(
                method=self.method,
                url=self.url,
                headers=self.headers,
                data=self.data,
                params=self.params,
                files=processed_files,
                timeout=self.timeout,
                verify=self.verify
            )
            response_time = int((time.time() - start_time) * 1000)

            self._cleanup_files()

            if self._should_stop:
                return

            response_text = self._decode_response(response)

            full_response_text = response_text
            if len(response_text) > MAX_RESPONSE_SIZE_DISPLAY:
                response_text = response_text[:MAX_RESPONSE_SIZE_DISPLAY] + RESPONSE_TRUNCATION_MESSAGE
                logging.info(f"Response truncated for display: {len(full_response_text)} bytes")

            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'cookies': dict(response.cookies),
                'text': response_text,
                'full_text': full_response_text if len(full_response_text) > MAX_RESPONSE_SIZE_DISPLAY else response_text,
                'response_time': response_time,
                'size': len(response.content),
                'truncated': len(full_response_text) > MAX_RESPONSE_SIZE_DISPLAY
            }
            logging.info(f"Request completed with status {response.status_code} in {response_time}ms")
            self.finished.emit(result)

        except requests.exceptions.Timeout as e:
            self._cleanup_files()
            if not self._should_stop:
                logging.error(f"Request timeout: {str(e)}")
                self.error.emit(f"Request timed out: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            self._cleanup_files()
            if not self._should_stop:
                logging.error(f"Connection error: {str(e)}")
                self.error.emit(f"Connection failed: {str(e)}")
        except requests.exceptions.HTTPError as e:
            self._cleanup_files()
            if not self._should_stop:
                logging.error(f"HTTP error: {str(e)}")
                self.error.emit(f"HTTP error: {str(e)}")
        except requests.exceptions.RequestException as e:
            self._cleanup_files()
            if not self._should_stop:
                logging.error(f"Request error: {str(e)}")
                self.error.emit(f"Request failed: {str(e)}")
        except FileNotFoundError as e:
            self._cleanup_files()
            if not self._should_stop:
                logging.error(f"File not found: {str(e)}")
                self.error.emit(f"File not found: {str(e)}")
        except ValueError as e:
            self._cleanup_files()
            if not self._should_stop:
                logging.error(f"Value error: {str(e)}")
                self.error.emit(f"Invalid value: {str(e)}")
        except Exception as e:
            self._cleanup_files()
            if not self._should_stop:
                logging.error(f"Unexpected error: {str(e)}")
                self.error.emit(f"Unexpected error: {str(e)}")

    def _prepare_files(self):
        """Prepare files for upload with proper resource tracking"""
        if not self.files:
            return None
        
        processed_files = {}
        for key, value in self.files.items():
            if isinstance(value, str):
                if not os.path.exists(value):
                    raise FileNotFoundError(f"File not found: {value}")
                if not os.path.isfile(value):
                    raise ValueError(f"Path is not a file: {value}")
                file_obj = open(value, 'rb')
                self._opened_files.append(file_obj)
                processed_files[key] = (os.path.basename(value), file_obj)
            elif isinstance(value, tuple) and len(value) > 1 and hasattr(value[1], 'read'):
                processed_files[key] = value
                self._opened_files.append(value[1])
            elif hasattr(value, 'read'):
                processed_files[key] = value
                self._opened_files.append(value)
            else:
                processed_files[key] = value
        
        return processed_files

    def _decode_response(self, response):
        """Safely decode response content to text"""
        try:
            return response.text
        except (UnicodeDecodeError, AttributeError):
            try:
                return response.content.decode('utf-8', errors='replace')
            except Exception:
                return f"[Binary content: {len(response.content)} bytes]"