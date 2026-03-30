import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .extractors import BaseExtractor, ExtractorFactory


@dataclass
class ChainingVariable:
    name: str
    value: Any
    extractor_type: str
    source_path: str
    created_at: float = 0


class ChainingEngine:
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self._variable_history: List[ChainingVariable] = []
        self._placeholder_pattern = re.compile(r'\{\{([^}]+)\}\}')

    def extract(self, extractor: BaseExtractor, response: Dict, variable_name: str) -> Optional[Any]:
        value = extractor.extract(response)
        if value is not None:
            self.set(variable_name, value)
            return value
        return None

    def extract_from_response(self, extractor_type: str, config: Dict, response: Dict, variable_name: str) -> Optional[Any]:
        extractor = ExtractorFactory.create(extractor_type, config)
        if not extractor:
            return None
        return self.extract(extractor, response, variable_name)

    def set(self, name: str, value: Any):
        self.variables[name] = value

    def get(self, name: str) -> Optional[Any]:
        return self.variables.get(name)

    def has(self, name: str) -> bool:
        return name in self.variables

    def remove(self, name: str) -> bool:
        if name in self.variables:
            del self.variables[name]
            return True
        return False

    def clear(self):
        self.variables.clear()
        self._variable_history.clear()

    def to_dict(self) -> Dict[str, Any]:
        return self.variables.copy()

    @classmethod
    def from_dict(cls, data: Dict) -> 'ChainingEngine':
        engine = cls()
        engine.variables = data.copy()
        return engine

    def apply_to_text(self, text: str) -> str:
        if not text:
            return text
        
        def replace_placeholder(match):
            var_name = match.group(1).strip()
            value = self.variables.get(var_name)
            if value is not None:
                return str(value)
            return match.group(0)
        
        return self._placeholder_pattern.sub(replace_placeholder, text)

    def apply_to_request(self, request_data: Dict) -> Dict:
        result = request_data.copy()
        
        if 'url' in result:
            result['url'] = self.apply_to_text(result['url'])
        
        if 'headers' in result:
            result['headers'] = {
                k: self.apply_to_text(v) for k, v in result['headers'].items()
            }
        
        if 'params' in result:
            result['params'] = {
                k: self.apply_to_text(v) for k, v in result['params'].items()
            }
        
        if 'body' in result and result['body']:
            result['body'] = self.apply_to_text(result['body'])
        
        return result

    def get_all_placeholders(self, text: str) -> List[str]:
        if not text:
            return []
        return [m.group(1).strip() for m in self._placeholder_pattern.finditer(text)]

    def has_pending_placeholders(self, text: str) -> bool:
        if not text:
            return False
        placeholders = self.get_all_placeholders(text)
        return any(p not in self.variables for p in placeholders)

    def get_pending_placeholders(self, text: str) -> List[str]:
        if not text:
            return []
        return [p for p in self.get_all_placeholders(text) if p not in self.variables]

    def export_variables(self) -> str:
        return json.dumps(self.variables, indent=2, default=str)

    def import_variables(self, json_str: str) -> bool:
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                self.variables.update(data)
                return True
        except json.JSONDecodeError:
            pass
        return False

    def list_variables(self) -> List[Dict[str, Any]]:
        return [
            {'name': name, 'value': value, 'type': type(value).__name__}
            for name, value in self.variables.items()
        ]
