import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, response: Dict) -> Optional[Any]:
        pass

    @abstractmethod
    def validate_config(self, config: Dict) -> bool:
        pass

    @property
    @abstractmethod
    def extractor_type(self) -> str:
        pass


class JSONPathExtractor(BaseExtractor):
    def __init__(self, path: str):
        self.path = path
        self._compiled_path = self._compile_path(path)

    def _compile_path(self, path: str) -> List[str]:
        clean_path = path.replace('$.', '').replace('$.', '')
        return [p for p in clean_path.split('.') if p]

    def extract(self, response: Dict) -> Optional[Any]:
        try:
            body = response.get('text', '')
            data = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            return None
        
        return self._navigate_path(data, self._compiled_path)

    def _navigate_path(self, data: Any, path_parts: List[str]) -> Optional[Any]:
        if not path_parts:
            return data
        
        current = data
        for part in path_parts:
            if current is None:
                return None
            
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    if part.isdigit():
                        current = current[int(part)]
                    else:
                        return None
                except (IndexError, ValueError):
                    return None
            else:
                return None
        
        return current

    def validate_config(self, config: Dict) -> bool:
        return 'path' in config and isinstance(config['path'], str)

    @property
    def extractor_type(self) -> str:
        return 'jsonpath'


class HeaderExtractor(BaseExtractor):
    def __init__(self, header_name: str):
        self.header_name = header_name

    def extract(self, response: Dict) -> Optional[str]:
        headers = response.get('headers', {})
        header_lower = self.header_name.lower()
        
        for key, value in headers.items():
            if key.lower() == header_lower:
                return value
        
        return None

    def validate_config(self, config: Dict) -> bool:
        return 'header_name' in config and isinstance(config['header_name'], str)

    @property
    def extractor_type(self) -> str:
        return 'header'


class RegexExtractor(BaseExtractor):
    def __init__(self, pattern: str, group: int = 0, flags: int = 0):
        self.pattern = pattern
        self.group = group
        self._regex = re.compile(pattern, flags)

    def extract(self, response: Dict) -> Optional[str]:
        body = response.get('text', '')
        match = self._regex.search(body)
        if match:
            try:
                return match.group(self.group)
            except IndexError:
                return match.group(0) if match.groups() else None
        return None

    def validate_config(self, config: Dict) -> bool:
        return 'pattern' in config and isinstance(config['pattern'], str)

    @property
    def extractor_type(self) -> str:
        return 'regex'


class CookieExtractor(BaseExtractor):
    def __init__(self, cookie_name: str):
        self.cookie_name = cookie_name

    def extract(self, response: Dict) -> Optional[str]:
        cookies = response.get('cookies', {})
        cookie_lower = self.cookie_name.lower()
        
        for key, value in cookies.items():
            if key.lower() == cookie_lower:
                return value
        
        return None

    def validate_config(self, config: Dict) -> bool:
        return 'cookie_name' in config and isinstance(config['cookie_name'], str)

    @property
    def extractor_type(self) -> str:
        return 'cookie'


class StatusCodeExtractor(BaseExtractor):
    def extract(self, response: Dict) -> Optional[int]:
        return response.get('status_code')

    def validate_config(self, config: Dict) -> bool:
        return True

    @property
    def extractor_type(self) -> str:
        return 'status_code'


class ExtractorFactory:
    _extractors = {
        'jsonpath': JSONPathExtractor,
        'header': HeaderExtractor,
        'regex': RegexExtractor,
        'cookie': CookieExtractor,
        'status_code': StatusCodeExtractor,
    }

    @classmethod
    def create(cls, extractor_type: str, config: Dict) -> Optional[BaseExtractor]:
        extractor_class = cls._extractors.get(extractor_type)
        if not extractor_class:
            return None
        
        try:
            if extractor_type == 'jsonpath':
                return extractor_class(config.get('path', ''))
            elif extractor_type == 'header':
                return extractor_class(config.get('header_name', ''))
            elif extractor_type == 'regex':
                return extractor_class(
                    config.get('pattern', ''),
                    config.get('group', 0),
                    config.get('flags', 0)
                )
            elif extractor_type == 'cookie':
                return extractor_class(config.get('cookie_name', ''))
            elif extractor_type == 'status_code':
                return extractor_class()
        except Exception:
            return None
        
        return None

    @classmethod
    def available_types(cls) -> List[str]:
        return list(cls._extractors.keys())
