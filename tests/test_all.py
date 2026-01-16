"""
Test runner to run all tests
"""
import pytest

# This file can be used to run all tests at once
# Run with: pytest tests/test_all.py

if __name__ == '__main__':
    pytest.main(['-v', 'tests/'])
