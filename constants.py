# Constants for pyPost

# HTTP Methods
HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']

# WebSocket Method (special handling)
METHOD_WEBSOCKET = 'WebSocket'

# Authentication Types
AUTH_NO_AUTH = 'No Auth'
AUTH_BEARER_TOKEN = 'Bearer Token'
AUTH_BASIC = 'Basic Auth'
AUTH_TYPES = [AUTH_NO_AUTH, AUTH_BEARER_TOKEN, AUTH_BASIC]

# Body Types
BODY_NONE = 'None'
BODY_JSON = 'JSON'
BODY_XML = 'XML'
BODY_PLAIN_TEXT = 'Plain Text'
BODY_MULTIPART = 'Multipart Form-Data'
BODY_BINARY = 'Binary'
BODY_GRAPHQL = 'GraphQL'
BODY_TYPES = [BODY_NONE, BODY_JSON, BODY_XML, BODY_PLAIN_TEXT, BODY_MULTIPART, BODY_BINARY, BODY_GRAPHQL]

# Default environment name
DEFAULT_ENV = 'Default'

# Response handling limits
MAX_RESPONSE_SIZE_DISPLAY = 1024 * 1024  # 1MB for display
MAX_RESPONSE_SIZE_LOG = 10 * 1024 * 1024  # 10MB for logging
RESPONSE_TRUNCATION_MESSAGE = "\n\n[Response truncated due to size. Full response saved to history.]"

# Assertion Types
ASSERTION_STATUS_CODE = 'status_code'
ASSERTION_JSON_PATH = 'json_path'
ASSERTION_HEADER = 'header'
ASSERTION_RESPONSE_TIME = 'response_time'
ASSERTION_BODY_CONTAINS = 'body_contains'
ASSERTION_TYPES = [
    ASSERTION_STATUS_CODE,
    ASSERTION_JSON_PATH,
    ASSERTION_HEADER,
    ASSERTION_RESPONSE_TIME,
    ASSERTION_BODY_CONTAINS,
]

# Extractor Types
EXTRACTOR_JSONPATH = 'jsonpath'
EXTRACTOR_HEADER = 'header'
EXTRACTOR_REGEX = 'regex'
EXTRACTOR_COOKIE = 'cookie'
EXTRACTOR_STATUS_CODE = 'status_code'
EXTRACTOR_TYPES = [
    EXTRACTOR_JSONPATH,
    EXTRACTOR_HEADER,
    EXTRACTOR_REGEX,
    EXTRACTOR_COOKIE,
    EXTRACTOR_STATUS_CODE,
]