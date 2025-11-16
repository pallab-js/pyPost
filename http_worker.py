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

    def __init__(self, method: str, url: str, headers: Dict, data: Optional[str] = None, params: Optional[Dict] = None, verify: bool = True, files: Optional[Dict] = None, db_manager=None, use_cache: bool = False):
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
        self._should_stop = False
        self._session = None

    def cancel(self):
        """Cancel the ongoing request"""
        self._should_stop = True

    def run(self):
        opened_files = []
        try:
            if self._should_stop:
                return

            logging.info(f"Sending {self.method} request to {self.url}")

            # Check cache first if enabled and it's a GET request
            if self.use_cache and self.db_manager and self.method.upper() == 'GET':
                cache_key = self.db_manager.get_cache_key(self.method, self.url, self.headers, self.data)
                cached_response = self.db_manager.get_cached_response(cache_key)
                if cached_response:
                    logging.info("Returning cached response")
                    result = {
                        'status_code': cached_response['status_code'],
                        'headers': eval(cached_response['headers']) if cached_response['headers'] else {},
                        'cookies': {},
                        'text': cached_response['response_data'],
                        'response_time': 0,  # Cached response has no response time
                        'size': len(cached_response['response_data'].encode()),
                        'cached': True
                    }
                    self.finished.emit(result)
                    return
            
            # Handle file uploads - open files in worker thread
            processed_files = None
            if self.files:
                processed_files = {}
                for key, value in self.files.items():
                    if isinstance(value, str):  # File path string
                        if not os.path.exists(value):
                            raise FileNotFoundError(f"File not found: {value}")
                        if not os.path.isfile(value):
                            raise ValueError(f"Path is not a file: {value}")
                        # Open file in binary mode
                        file_obj = open(value, 'rb')
                        opened_files.append(file_obj)
                        # Format: (filename, file_obj, content_type) or just file_obj
                        processed_files[key] = (os.path.basename(value), file_obj)
                    elif isinstance(value, tuple):
                        # Already a tuple (filename, file_obj) or (filename, file_obj, content_type)
                        processed_files[key] = value
                        if len(value) > 1 and hasattr(value[1], 'read'):
                            opened_files.append(value[1])
                    else:
                        # File object already
                        processed_files[key] = value
                        opened_files.append(value)

            if self._should_stop:
                # Clean up files if cancelled before request
                for file_obj in opened_files:
                    try:
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
                    except Exception:
                        pass
                return

            start_time = time.time()
            self._session = requests.Session()
            
            # Check cancellation again before making request
            if self._should_stop:
                for file_obj in opened_files:
                    try:
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
                    except Exception:
                        pass
                return
            
            response = self._session.request(
                method=self.method,
                url=self.url,
                headers=self.headers,
                data=self.data,
                params=self.params,
                files=processed_files,
                timeout=30,
                verify=self.verify
            )
            response_time = int((time.time() - start_time) * 1000)

            # Close files after request
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception as e:
                    logging.warning(f"Error closing file: {e}")

            if self._should_stop:
                return

            # Handle response text safely - may fail for binary content
            try:
                # Try to decode as text, fallback to base64 for binary
                response_text = response.text
            except (UnicodeDecodeError, AttributeError):
                # If decoding fails, treat as binary
                try:
                    # Try UTF-8 with error handling
                    response_text = response.content.decode('utf-8', errors='replace')
                except Exception:
                    # Last resort: show as binary data indicator
                    response_text = f"[Binary content: {len(response.content)} bytes]"

            # Handle large responses
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
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"Request timeout: {str(e)}")
                self.error.emit(f"Request timed out: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"Connection error: {str(e)}")
                self.error.emit(f"Connection failed: {str(e)}")
        except requests.exceptions.HTTPError as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"HTTP error: {str(e)}")
                self.error.emit(f"HTTP error: {str(e)}")
        except requests.exceptions.RequestException as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"Request error: {str(e)}")
                self.error.emit(f"Request failed: {str(e)}")
        except FileNotFoundError as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"File not found: {str(e)}")
                self.error.emit(f"File not found: {str(e)}")
        except ValueError as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"Value error: {str(e)}")
                self.error.emit(f"Invalid value: {str(e)}")
        except Exception as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"Unexpected error: {str(e)}")
                self.error.emit(f"Unexpected error: {str(e)}")