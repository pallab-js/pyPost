import time
import os
import requests
import logging
from typing import Dict, Optional
from PySide6.QtCore import QThread, Signal


class HTTPWorker(QThread):
    """Worker thread for HTTP requests to keep UI responsive"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, method: str, url: str, headers: Dict, data: Optional[str] = None, params: Optional[Dict] = None, verify: bool = True, files: Optional[Dict] = None):
        super().__init__()
        self.method = method
        self.url = url
        self.headers = headers
        self.data = data
        self.params = params
        self.verify = verify
        self.files = files
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

            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'cookies': dict(response.cookies),
                'text': response_text,
                'response_time': response_time,
                'size': len(response.content)
            }
            logging.info(f"Request completed with status {response.status_code} in {response_time}ms")
            self.finished.emit(result)

        except requests.exceptions.RequestException as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"Request failed: {str(e)}")
                self.error.emit(str(e))
        except (FileNotFoundError, ValueError) as e:
            # Close files on error
            for file_obj in opened_files:
                try:
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                except Exception:
                    pass
            if not self._should_stop:
                logging.error(f"File error: {str(e)}")
                self.error.emit(str(e))