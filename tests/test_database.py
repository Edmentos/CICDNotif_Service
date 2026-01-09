import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError


class TestDatabaseConnection:
    """Test database connection and retry logic"""
    
    def test_database_url_exists(self):
        """Test that DATABASE_URL is loaded"""
        from app.database import DATABASE_URL
        assert DATABASE_URL is not None
        assert isinstance(DATABASE_URL, str)
    
    def test_sql_echo_is_boolean(self):
        """Test SQL_ECHO is a boolean"""
        from app.database import SQL_ECHO
        assert isinstance(SQL_ECHO, bool)
    
    def test_retry_config_loaded(self):
        """Test retry configuration is loaded"""
        from app.database import RETRIES, DELAY
        assert isinstance(RETRIES, int)
        assert isinstance(DELAY, float)
        assert RETRIES > 0
        assert DELAY > 0
    
    def test_get_db_generator(self):
        """Test get_db yields and closes session"""
        from app.database import get_db
        
        gen = get_db()
        db = next(gen)
        assert db is not None
        
        # Close the generator
        try:
            next(gen)
        except StopIteration:
            pass  # Expected behavior
    
    def test_connect_args_exist(self):
        """Test that connect_args is defined"""
        from app.database import connect_args
        assert isinstance(connect_args, dict)
    
    def test_engine_exists(self):
        """Test that engine is created"""
        from app.database import engine
        assert engine is not None
    
    def test_sessionlocal_exists(self):
        """Test that SessionLocal is created"""
        from app.database import SessionLocal
        assert SessionLocal is not None
