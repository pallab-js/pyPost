# Constants for pyPost

# HTTP Methods
HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']

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
BODY_TYPES = [BODY_NONE, BODY_JSON, BODY_XML, BODY_PLAIN_TEXT, BODY_MULTIPART, BODY_BINARY]

# Default environment name
DEFAULT_ENV = 'Default'