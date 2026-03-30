import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_generator import (
    DataGenerator,
    DataType,
    DataTemplate,
    GeneratedData,
    TemplateEngine,
)


class TestDataGenerator:
    def setup_method(self):
        self.gen = DataGenerator(seed=42)

    def test_first_name(self):
        name = self.gen.first_name()
        assert isinstance(name, str)
        assert len(name) > 0
        assert name[0].isupper()

    def test_last_name(self):
        name = self.gen.last_name()
        assert isinstance(name, str)
        assert len(name) > 0
        assert name[0].isupper()

    def test_full_name(self):
        name = self.gen.full_name()
        assert " " in name
        parts = name.split()
        assert len(parts) == 2

    def test_email(self):
        email = self.gen.email()
        assert "@" in email
        assert "." in email.split("@")[1]

    def test_email_with_params(self):
        email = self.gen.email(first_name="John", domain="example.com")
        assert "john" in email.lower()
        assert "example.com" in email

    def test_username(self):
        username = self.gen.username()
        assert isinstance(username, str)
        assert len(username) > 0

    def test_password(self):
        pwd = self.gen.password()
        assert len(pwd) == 12
        assert any(c.isupper() for c in pwd)
        assert any(c.isdigit() for c in pwd)

    def test_password_custom_length(self):
        pwd = self.gen.password(length=20)
        assert len(pwd) == 20

    def test_phone(self):
        phone = self.gen.phone()
        assert "(" in phone or phone.startswith("+")

    def test_address(self):
        addr = self.gen.address()
        assert isinstance(addr, str)
        assert len(addr) > 0

    def test_city(self):
        city = self.gen.city()
        assert city in DataGenerator.CITIES

    def test_state(self):
        state = self.gen.state()
        assert state in DataGenerator.STATES

    def test_country(self):
        country = self.gen.country()
        assert country in DataGenerator.COUNTRIES

    def test_zip_code(self):
        zip_code = self.gen.zip_code()
        assert isinstance(zip_code, str)
        assert len(zip_code) == 5

    def test_company(self):
        company = self.gen.company()
        assert isinstance(company, str)
        assert len(company) > 0

    def test_job_title(self):
        title = self.gen.job_title()
        assert title in DataGenerator.JOB_TITLES

    def test_uuid(self):
        uuid_val = self.gen.uuid()
        assert len(uuid_val) == 36
        assert "-" in uuid_val

    def test_integer(self):
        val = self.gen.integer()
        assert isinstance(val, int)
        assert 0 <= val <= 1000

    def test_integer_custom_range(self):
        val = self.gen.integer(min_val=100, max_val=200)
        assert 100 <= val <= 200

    def test_float(self):
        val = self.gen.float()
        assert isinstance(val, float)
        assert 0.0 <= val <= 1000.0

    def test_float_custom_range(self):
        val = self.gen.float(min_val=10.0, max_val=20.0)
        assert 10.0 <= val <= 20.0

    def test_boolean(self):
        val = self.gen.boolean()
        assert isinstance(val, bool)

    def test_date(self):
        date = self.gen.date()
        assert "-" in date
        assert len(date) == 10

    def test_datetime(self):
        dt = self.gen.datetime()
        assert "-" in dt
        assert ":" in dt

    def test_url(self):
        url = self.gen.url()
        assert url.startswith("https://") or url.startswith("http://")
        assert "." in url

    def test_ip_address(self):
        ip = self.gen.ip_address()
        parts = ip.split(".")
        assert len(parts) == 4

    def test_ip_v6(self):
        ip = self.gen.ip_address(version="v6")
        assert ":" in ip

    def test_mac_address(self):
        mac = self.gen.mac_address()
        parts = mac.split(":")
        assert len(parts) == 6

    def test_user_agent(self):
        ua = self.gen.user_agent()
        assert "Mozilla" in ua

    def test_credit_card(self):
        cc = self.gen.credit_card()
        assert len(cc) == 15 or len(cc) == 16
        assert cc.isdigit()

    def test_iban(self):
        iban = self.gen.iban()
        assert len(iban) >= 15

    def test_color(self):
        color = self.gen.color()
        assert isinstance(color, str)
        assert len(color) > 0

    def test_hex_color(self):
        color = self.gen.hex_color()
        assert color.startswith("#")
        assert len(color) == 7

    def test_rgb_color(self):
        color = self.gen.rgb_color()
        assert color.startswith("rgb(")

    def test_text(self):
        text = self.gen.text(length=100)
        assert len(text) == 100

    def test_sentence(self):
        sentence = self.gen.sentence()
        assert sentence.endswith(".")

    def test_paragraph(self):
        para = self.gen.paragraph(sentences_count=3)
        assert para.count(".") >= 3

    def test_word(self):
        word = self.gen.word()
        assert isinstance(word, str)
        assert word in DataGenerator.WORDS

    def test_generate(self):
        result = self.gen.generate(DataType.EMAIL, "user_email")
        assert isinstance(result, GeneratedData)
        assert result.key == "user_email"
        assert "@" in result.value


class TestTemplateEngine:
    def setup_method(self):
        self.engine = TemplateEngine(DataGenerator(seed=42))

    def test_simple_template(self):
        result = self.engine.generate_from_template("Hello {{first_name}}!")
        assert "Hello" in result
        assert "!" in result

    def test_multiple_placeholders(self):
        result = self.engine.generate_from_template(
            "{{first_name}} {{last_name}} - {{email}}"
        )
        parts = result.split(" - ")
        assert len(parts) == 2

    def test_uuid_template(self):
        result = self.engine.generate_from_template("ID: {{uuid}}")
        assert "ID:" in result

    def test_integer_template(self):
        result = self.engine.generate_from_template("Count: {{integer}}")
        assert "Count:" in result

    def test_text_template(self):
        result = self.engine.generate_from_template("{{text(50)}}")
        assert len(result) == 50

    def test_number_between_template(self):
        result = self.engine.generate_from_template("{{number_between(10, 20)}}")
        num = int(result)
        assert 10 <= num <= 20

    def test_password_template(self):
        result = self.engine.generate_from_template("Password: {{password(16)}}")
        assert len(result.replace("Password: ", "")) == 16

    def test_custom_variable(self):
        result = self.engine.generate_from_template(
            "Hello {name}!", variables={"name": "John"}
        )
        assert "John" in result

    def test_batch_generation(self):
        results = self.engine.generate_batch("User: {{username}}", 3)
        assert len(results) == 3
        assert all("User:" in r for r in results)


class TestDataTemplate:
    def test_template_creation(self):
        template = DataTemplate(
            name="user_template",
            data_type=DataType.EMAIL,
            options={"domain": "example.com"}
        )
        assert template.name == "user_template"
        assert template.data_type == DataType.EMAIL


class TestGeneratedData:
    def test_generated_data_creation(self):
        data = GeneratedData(
            key="email",
            value="test@example.com",
            data_type=DataType.EMAIL
        )
        assert data.key == "email"
        assert data.value == "test@example.com"
        assert data.data_type == DataType.EMAIL


class TestDataTypeEnum:
    def test_data_types(self):
        assert DataType.FIRST_NAME.value == "first_name"
        assert DataType.EMAIL.value == "email"
        assert DataType.UUID.value == "uuid"
        assert DataType.PASSWORD.value == "password"

    def test_all_types_exist(self):
        assert len(DataType) > 20
