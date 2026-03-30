import random
import string
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import re


class DataType(Enum):
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    EMAIL = "email"
    USERNAME = "username"
    PASSWORD = "password"
    PHONE = "phone"
    ADDRESS = "address"
    CITY = "city"
    STATE = "state"
    COUNTRY = "country"
    ZIP_CODE = "zip_code"
    COMPANY = "company"
    JOB_TITLE = "job_title"
    UUID = "uuid"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    URL = "url"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    USER_AGENT = "user_agent"
    CREDIT_CARD = "credit_card"
    IBAN = "iban"
    COLOR = "color"
    NUMBER_BETWEEN = "number_between"
    TEXT = "text"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    WORD = "word"
    HEX_COLOR = "hex_color"
    RGB_COLOR = "rgb_color"


@dataclass
class DataTemplate:
    name: str
    data_type: DataType
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedData:
    key: str
    value: Any
    data_type: DataType


class DataGenerator:
    FIRST_NAMES = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley",
        "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
        "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    ]

    CITIES = [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
        "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
        "Fort Worth", "Columbus", "Charlotte", "Seattle", "Denver", "Boston", "Detroit",
    ]

    STATES = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
        "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
        "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
        "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    ]

    COUNTRIES = [
        "United States", "Canada", "Mexico", "United Kingdom", "Germany", "France",
        "Spain", "Italy", "Australia", "Japan", "China", "India", "Brazil", "Argentina",
    ]

    STREETS = [
        "Main", "Oak", "Maple", "Cedar", "Pine", "Elm", "Washington", "Lake",
        "Hill", "Park", "Walnut", "Sunset", "River", "Spring", "Forest", "Valley",
    ]

    STREET_TYPES = ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Ct", "Way", "Pl"]

    JOB_TITLES = [
        "Software Engineer", "Product Manager", "Data Analyst", "Designer", "Marketing Manager",
        "Sales Representative", "Accountant", "HR Coordinator", "Project Manager", "CEO",
        "CTO", "CFO", "VP of Engineering", "Director of Sales", "Chief Marketing Officer",
    ]

    DOMAINS = [
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com",
        "protonmail.com", "icloud.com", "mail.com", "zoho.com", "fastmail.com",
    ]

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
    ]

    WORDS = [
        "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing",
        "elit", "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore",
        "dolore", "magna", "aliqua", "enim", "minim", "veniam", "quis", "nostrud",
    ]

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def _random_choice(self, choices: List[str]) -> str:
        return random.choice(choices)

    def first_name(self) -> str:
        return self._random_choice(self.FIRST_NAMES)

    def last_name(self) -> str:
        return self._random_choice(self.LAST_NAMES)

    def full_name(self) -> str:
        return f"{self.first_name()} {self.last_name()}"

    def email(self, first_name: Optional[str] = None, last_name: Optional[str] = None,
              domain: Optional[str] = None) -> str:
        fn = first_name or self.first_name()
        ln = last_name or self.last_name()
        d = domain or self._random_choice(self.DOMAINS)
        separator = random.choice([".", "_", ""])
        number = random.randint(0, 999) if random.random() > 0.5 else ""
        return f"{fn.lower()}{separator}{ln.lower()}{number}@{d}"

    def username(self, first_name: Optional[str] = None, last_name: Optional[str] = None) -> str:
        fn = (first_name or self.first_name()).lower()
        ln = (last_name or self.last_name()).lower()
        separator = random.choice([".", "_", ""])
        number = random.randint(1, 999)
        pattern = random.choice([
            f"{fn}{separator}{ln}",
            f"{fn[0]}{ln}",
            f"{fn}{ln[0]}",
            f"{fn}{separator}{ln}{number}",
            f"{fn}{ln}{number}",
        ])
        return pattern

    def password(self, length: int = 12) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(random.choice(chars) for _ in range(length))

    def phone(self, format: str = "US") -> str:
        if format == "US":
            area = random.randint(200, 999)
            exchange = random.randint(200, 999)
            subscriber = random.randint(1000, 9999)
            return f"({area}) {exchange}-{subscriber}"
        elif format == "INTL":
            return f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(1000, 9999)}"
        return f"+{random.randint(1000000000, 9999999999)}"

    def address(self) -> str:
        num = random.randint(1, 9999)
        street = self._random_choice(self.STREETS)
        stype = self._random_choice(self.STREET_TYPES)
        return f"{num} {street} {stype}"

    def city(self) -> str:
        return self._random_choice(self.CITIES)

    def state(self) -> str:
        return self._random_choice(self.STATES)

    def country(self) -> str:
        return self._random_choice(self.COUNTRIES)

    def zip_code(self, state: Optional[str] = None) -> str:
        if state == "NY":
            return f"1{random.randint(0, 4)}{random.randint(10000, 14999)}"
        return f"{random.randint(10000, 99999)}"

    def company(self) -> str:
        prefixes = ["", "Global", "Tech", "Digital", "Smart", "Prime", "Elite"]
        suffixes = ["Inc", "LLC", "Corp", "Ltd", "Solutions", "Systems", "Group"]
        prefix = self._random_choice(prefixes)
        suffix = self._random_choice(suffixes)
        if prefix:
            return f"{prefix} {suffix}"
        return suffix

    def job_title(self) -> str:
        return self._random_choice(self.JOB_TITLES)

    def uuid(self) -> str:
        return str(uuid.uuid4())

    def integer(self, min_val: int = 0, max_val: int = 1000) -> int:
        return random.randint(min_val, max_val)

    def float(self, min_val: float = 0.0, max_val: float = 1000.0, decimals: int = 2) -> float:
        value = random.uniform(min_val, max_val)
        return round(value, decimals)

    def boolean(self) -> bool:
        return random.choice([True, False])

    def date(self, start: Optional[str] = None, end: Optional[str] = None, 
             fmt: str = "%Y-%m-%d") -> str:
        if start:
            start_date = datetime.strptime(start, fmt)
        else:
            start_date = datetime.now() - timedelta(days=365)
        if end:
            end_date = datetime.strptime(end, fmt)
        else:
            end_date = datetime.now() + timedelta(days=365)
        delta = end_date - start_date
        random_days = random.randint(0, delta.days)
        return (start_date + timedelta(days=random_days)).strftime(fmt)

    def datetime(self, start: Optional[str] = None, end: Optional[str] = None,
                 fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        if start:
            start_dt = datetime.strptime(start, fmt)
        else:
            start_dt = datetime.now() - timedelta(days=365)
        if end:
            end_dt = datetime.strptime(end, fmt)
        else:
            end_dt = datetime.now() + timedelta(days=365)
        delta = end_dt - start_dt
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return (start_dt + timedelta(seconds=random_seconds)).strftime(fmt)

    def time(self, fmt: str = "%H:%M:%S") -> str:
        return datetime.now().strftime(fmt)

    def url(self, scheme: str = "https") -> str:
        domain = self.company().lower().replace(" ", "").replace(".", "")[:10]
        tld = random.choice(["com", "io", "net", "org", "dev"])
        path = random.choice(["", f"/{self.word()}", f"/{self.word()}/{self.word()}"])
        return f"{scheme}://{domain}.{tld}{path}"

    def ip_address(self, version: str = "v4") -> str:
        if version == "v4":
            return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
        return f"{random.randint(0,65535):x}:{random.randint(0,65535):x}:{random.randint(0,65535):x}:{random.randint(0,65535):x}"

    def mac_address(self) -> str:
        return ":".join(f"{random.randint(0,255):02x}" for _ in range(6))

    def user_agent(self) -> str:
        return self._random_choice(self.USER_AGENTS)

    def credit_card(self, provider: Optional[str] = None) -> str:
        if provider == "VISA":
            prefix = "4"
        elif provider == "MC":
            prefix = random.choice(["51", "52", "53", "54", "55"])
        elif provider == "AMEX":
            prefix = random.choice(["34", "37"])
        elif provider == "DISCOVER":
            prefix = "6011"
        else:
            prefix = random.choice(["4", "51", "52", "53", "54", "55", "34", "37", "6011"])
        
        number = prefix + "".join(str(random.randint(0, 9)) for _ in range(14 - len(prefix)))
        checksum = self._luhn_checksum(number)
        return number + str((10 - checksum) % 10)

    def _luhn_checksum(self, card_number: str) -> int:
        def digits_of(n):
            return [int(d) for d in str(n)]
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10

    def iban(self) -> str:
        country = random.choice(["DE", "GB", "FR", "ES", "IT", "NL", "BE", "AT", "CH", "SE"])
        check = f"{random.randint(10, 99)}"
        bban = "".join(str(random.randint(0, 9)) for _ in range(18))
        return f"{country}{check}{bban}"

    def color(self) -> str:
        return self._random_choice(["Red", "Blue", "Green", "Yellow", "Purple", "Orange", "Pink", "Brown", "Black", "White"])

    def number_between(self, min_val: int, max_val: int) -> int:
        return self.integer(min_val, max_val)

    def text(self, length: int = 50) -> str:
        return "".join(random.choice(string.ascii_letters + string.digits + " ") for _ in range(length)).strip()

    def paragraph(self, sentences_count: int = 3) -> str:
        return " ".join(self.sentence() for _ in range(sentences_count))

    def sentence(self) -> str:
        word_count = random.randint(5, 15)
        words = [self.word().capitalize()] + [self.word() for _ in range(word_count - 1)]
        return " ".join(words) + "."

    def word(self) -> str:
        return self._random_choice(self.WORDS)

    def hex_color(self) -> str:
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    def rgb_color(self) -> str:
        return f"rgb({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)})"

    def generate(self, data_type: DataType, key: str, options: Optional[Dict[str, Any]] = None) -> GeneratedData:
        options = options or {}
        method = getattr(self, data_type.value, None)
        if method:
            value = method(**options) if options else method()
        else:
            value = None
        return GeneratedData(key=key, value=value, data_type=data_type)


class TemplateEngine:
    def __init__(self, generator: Optional[DataGenerator] = None):
        self.generator = generator or DataGenerator()

    def generate_from_template(self, template: str, variables: Optional[Dict[str, Any]] = None) -> str:
        result = template
        
        patterns = {
            r'\{\{uuid\}\}': lambda: self.generator.uuid(),
            r'\{\{integer\}\}': lambda: str(self.generator.integer()),
            r'\{\{float\}\}': lambda: str(self.generator.float()),
            r'\{\{boolean\}\}': lambda: str(self.generator.boolean()),
            r'\{\{first_name\}\}': lambda: self.generator.first_name(),
            r'\{\{last_name\}\}': lambda: self.generator.last_name(),
            r'\{\{full_name\}\}': lambda: self.generator.full_name(),
            r'\{\{email\}\}': lambda: self.generator.email(),
            r'\{\{username\}\}': lambda: self.generator.username(),
            r'\{\{phone\}\}': lambda: self.generator.phone(),
            r'\{\{address\}\}': lambda: self.generator.address(),
            r'\{\{city\}\}': lambda: self.generator.city(),
            r'\{\{state\}\}': lambda: self.generator.state(),
            r'\{\{country\}\}': lambda: self.generator.country(),
            r'\{\{zip\}\}': lambda: self.generator.zip_code(),
            r'\{\{company\}\}': lambda: self.generator.company(),
            r'\{\{job_title\}\}': lambda: self.generator.job_title(),
            r'\{\{date\}\}': lambda: self.generator.date(),
            r'\{\{datetime\}\}': lambda: self.generator.datetime(),
            r'\{\{url\}\}': lambda: self.generator.url(),
            r'\{\{ip\}\}': lambda: self.generator.ip_address(),
            r'\{\{color\}\}': lambda: self.generator.color(),
            r'\{\{hex_color\}\}': lambda: self.generator.hex_color(),
            r'\{\{rgb_color\}\}': lambda: self.generator.rgb_color(),
            r'\{\{word\}\}': lambda: self.generator.word(),
            r'\{\{sentence\}\}': lambda: self.generator.sentence(),
            r'\{\{paragraph\}\}': lambda: self.generator.paragraph(),
            r'\{\{text\((\d+)\)\}\}': lambda m: self.generator.text(int(m.group(1))),
            r'\{\{number_between\((\d+),\s*(\d+)\)\}\}': lambda m: str(self.generator.number_between(int(m.group(1)), int(m.group(2)))),
            r'\{\{password\((\d+)\)\}\}': lambda m: self.generator.password(int(m.group(1))),
        }

        patterns_simple = {
            r'\{\{(\w+)\}\}': lambda m: self.generator.username() if m.group(1) not in dir(self.generator) else str(getattr(self.generator, m.group(1))()),
        }

        for pattern, generator in patterns.items():
            if "(" in pattern:
                compiled = re.compile(pattern)
                result = compiled.sub(generator, result)
            else:
                result = result.replace(pattern, generator())

        for pattern, generator in patterns_simple.items():
            compiled = re.compile(pattern)
            result = compiled.sub(generator, result)

        if variables:
            for var_name, var_value in variables.items():
                result = result.replace(f"{{{var_name}}}", str(var_value))

        return result

    def generate_batch(self, template: str, count: int) -> List[str]:
        return [self.generate_from_template(template) for _ in range(count)]
