"""Pytest configuration and shared fixtures."""
import pytest
import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test', override=True)

# Set test environment
os.environ['ENVIRONMENT'] = 'test'

# For moto tests (unit tests), don't use LocalStack
# For integration tests, USE_LOCALSTACK will be set to 'true'
if not os.environ.get('USE_LOCALSTACK'):
    os.environ['USE_LOCALSTACK'] = 'false'
    os.environ['AWS_ENDPOINT_URL'] = ''


@pytest.fixture(scope='session')
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture
def use_moto(monkeypatch):
    """Fixture to ensure moto tests don't try to use LocalStack."""
    monkeypatch.setenv('USE_LOCALSTACK', 'false')
    monkeypatch.setenv('AWS_ENDPOINT_URL', '')
    # Force Config to reload
    import importlib
    import sys
    if 'shared.config' in sys.modules:
        importlib.reload(sys.modules['shared.config'])

