"""Pytest configuration and shared fixtures."""
import pytest
import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test', override=True)

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['USE_LOCALSTACK'] = 'true'
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'


@pytest.fixture(scope='session')
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'

