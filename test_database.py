import pytest
import os
from database import DatabaseManager


@pytest.fixture
def db_manager(tmp_path):
    """Fixture to create a DatabaseManager with temporary database"""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    yield db
    # Cleanup
    if os.path.exists(str(db_path)):
        os.remove(str(db_path))
    key_path = str(db_path).replace('.db', '.encryption_key')
    if os.path.exists(key_path):
        os.remove(key_path)


def test_init_database(db_manager):
    """Test database initialization"""
    # Check if tables exist
    result = db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row['name'] for row in result]
    expected_tables = ['collections', 'history', 'environments', 'environment_variables']
    for table in expected_tables:
        assert table in table_names


def test_execute_query(db_manager):
    """Test execute_query method"""
    # Insert test data
    db_manager.execute_update("INSERT INTO environments (name) VALUES (?)", ("TestEnv",))
    result = db_manager.execute_query("SELECT * FROM environments WHERE name = ?", ("TestEnv",))
    assert len(result) == 1
    assert result[0]['name'] == "TestEnv"


def test_execute_query_error(db_manager):
    """Test execute_query with invalid query"""
    with pytest.raises(Exception):
        db_manager.execute_query("SELECT * FROM nonexistent_table")


def test_execute_update(db_manager):
    """Test execute_update method"""
    last_id = db_manager.execute_update("INSERT INTO environments (name) VALUES (?)", ("TestEnv2",))
    assert last_id is not None
    result = db_manager.execute_query("SELECT * FROM environments WHERE id = ?", (last_id,))
    assert len(result) == 1


def test_execute_update_error(db_manager):
    """Test execute_update with invalid query"""
    with pytest.raises(Exception):
        db_manager.execute_update("INSERT INTO nonexistent_table VALUES (?)", ("test",))


def test_default_environment(db_manager):
    """Test that default environment is created"""
    result = db_manager.execute_query("SELECT * FROM environments")
    assert len(result) >= 1
    default_env = next((env for env in result if env['name'] == 'Default'), None)
    assert default_env is not None


def test_encrypt_decrypt(db_manager):
    """Test encryption and decryption"""
    test_data = "sensitive data"
    encrypted = db_manager.encrypt(test_data)
    assert encrypted != test_data
    decrypted = db_manager.decrypt(encrypted)
    assert decrypted == test_data


def test_encrypt_decrypt_error(db_manager):
    """Test decryption with invalid data"""
    with pytest.raises(Exception):
        db_manager.decrypt("invalid")


def test_collections_crud(db_manager):
    """Test collections CRUD operations"""
    # Create
    coll_id = db_manager.execute_update(
        "INSERT INTO collections (name, request_data) VALUES (?, ?)",
        ("Test Collection", '{"method": "GET"}')
    )
    assert coll_id is not None

    # Read
    result = db_manager.execute_query("SELECT * FROM collections WHERE id = ?", (coll_id,))
    assert len(result) == 1
    assert result[0]['name'] == "Test Collection"

    # Update
    db_manager.execute_update("UPDATE collections SET name = ? WHERE id = ?", ("Updated Collection", coll_id))
    result = db_manager.execute_query("SELECT * FROM collections WHERE id = ?", (coll_id,))
    assert result[0]['name'] == "Updated Collection"

    # Delete
    db_manager.execute_update("DELETE FROM collections WHERE id = ?", (coll_id,))
    result = db_manager.execute_query("SELECT * FROM collections WHERE id = ?", (coll_id,))
    assert len(result) == 0


def test_history_operations(db_manager):
    """Test history logging"""
    hist_id = db_manager.execute_update(
        "INSERT INTO history (method, url, request_data, response_data, status_code, response_time) VALUES (?, ?, ?, ?, ?, ?)",
        ("GET", "https://example.com", "{}", "{}", 200, 100)
    )
    assert hist_id is not None

    result = db_manager.execute_query("SELECT * FROM history WHERE id = ?", (hist_id,))
    assert len(result) == 1
    assert result[0]['method'] == "GET"
    assert result[0]['status_code'] == 200


def test_environment_variables(db_manager):
    """Test environment variables operations"""
    # Create environment
    env_id = db_manager.execute_update("INSERT INTO environments (name) VALUES (?)", ("TestEnv",))

    # Add variable
    var_id = db_manager.execute_update(
        "INSERT INTO environment_variables (environment_id, name, value) VALUES (?, ?, ?)",
        (env_id, "API_KEY", "secret")
    )
    assert var_id is not None

    # Query
    result = db_manager.execute_query(
        "SELECT * FROM environment_variables WHERE environment_id = ?",
        (env_id,)
    )
    assert len(result) == 1
    assert result[0]['name'] == "API_KEY"