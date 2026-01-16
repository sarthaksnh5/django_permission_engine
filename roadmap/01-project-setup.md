# Phase 1: Project Setup

## Overview

This phase covers setting up the project structure, development environment, and initial configuration.

## Step 1: Create Project Structure

### Directory Structure

```bash
django_permission_engine/
├── django_permission_engine/     # Main package
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── registry.py
│   ├── permissions.py
│   ├── views.py
│   ├── management/
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── upr_sync.py
│   │       └── upr_validate.py
│   └── migrations/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_registry.py
│   └── test_permissions.py
├── docs/                          # Documentation (already created)
├── roadmap/                       # This roadmap
├── setup.py
├── setup.cfg
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── LICENSE
├── .gitignore
├── .pre-commit-config.yaml
└── tox.ini
```

### Create Directory Structure

```bash
# Create main directories
mkdir -p django_permission_engine/management/commands
mkdir -p django_permission_engine/migrations
mkdir -p tests
mkdir -p docs
mkdir -p roadmap

# Create __init__.py files
touch django_permission_engine/__init__.py
touch django_permission_engine/management/__init__.py
touch django_permission_engine/management/commands/__init__.py
touch django_permission_engine/migrations/__init__.py
touch tests/__init__.py
```

## Step 2: Initialize Git Repository

### Create .gitignore

```bash
# .gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Environment
.env
.env.local

# Distribution
dist/
*.tar.gz
```

### Initialize Git

```bash
git init
git add .gitignore
git commit -m "Initial commit: Add .gitignore"
```

## Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

## Step 4: Create Requirements Files

### requirements.txt

```txt
# Core dependencies
Django>=3.2,<5.0
djangorestframework>=3.12,<4.0

# Optional but recommended
python-dateutil>=2.8.0
```

### requirements-dev.txt

```txt
# Include base requirements
-r requirements.txt

# Testing
pytest>=7.0.0
pytest-django>=4.5.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
factory-boy>=3.2.0

# Code quality
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
mypy>=1.0.0
pylint>=2.16.0

# Documentation
sphinx>=6.0.0
sphinx-rtd-theme>=1.2.0

# Development tools
ipython>=8.0.0
pre-commit>=3.0.0
```

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

## Step 5: Create setup.py

```python
# setup.py
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="django-permission-engine",
    version="0.1.0",
    description="Unified Permission Registry (UPR) for Django & DRF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/django-permission-engine",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "Django>=3.2,<5.0",
        "djangorestframework>=3.12,<4.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
    ],
    keywords="django permissions drf rest-framework",
    project_urls={
        "Documentation": "https://django-permission-engine.readthedocs.io/",
        "Source": "https://github.com/yourusername/django-permission-engine",
        "Tracker": "https://github.com/yourusername/django-permission-engine/issues",
    },
)
```

## Step 6: Create pyproject.toml

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.black]
line-length = 100
target-version = ['py38']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tests.settings"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.coverage.run]
source = ["django_permission_engine"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Step 7: Create setup.cfg

```ini
# setup.cfg
[metadata]
description-file = README.md

[flake8]
max-line-length = 100
exclude = 
    .git,
    __pycache__,
    build,
    dist,
    *.egg-info,
    venv,
    .venv,
    migrations
ignore = 
    E203,  # whitespace before ':'
    E501,  # line too long (handled by black)
    W503,  # line break before binary operator
```

## Step 8: Create Initial Package Files

### django_permission_engine/__init__.py

```python
"""
Django Permission Engine - Unified Permission Registry (UPR) for Django & DRF
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

default_app_config = "django_permission_engine.apps.PermissionEngineConfig"
```

### django_permission_engine/apps.py

```python
from django.apps import AppConfig


class PermissionEngineConfig(AppConfig):
    """Django app configuration for Permission Engine"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_permission_engine"
    verbose_name = "Permission Engine"

    def ready(self):
        """Called when Django starts"""
        # Import signal handlers, registry initialization, etc.
        pass
```

## Step 9: Create Test Settings

### tests/settings.py

```python
"""
Django settings for testing
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "test-secret-key-for-testing-only"

DEBUG = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "django_permission_engine",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# UPR Configuration
UPR_CONFIG = {
    "validate_on_startup": False,  # Disable for tests
    "strict_mode": False,
    "auto_sync": False,
}
```

### tests/urls.py

```python
"""URL configuration for tests"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
```

## Step 10: Create Pre-commit Configuration

### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.8

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
```

### Install Pre-commit Hooks

```bash
pre-commit install
```

## Step 11: Create LICENSE

Choose a license (MIT recommended):

```text
MIT License

Copyright (c) 2024 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Step 12: Create Initial README.md

```markdown
# Django Permission Engine

Unified Permission Registry (UPR) for Django & DRF

## Installation

```bash
pip install django-permission-engine
```

## Quick Start

[Add quick start example]

## Documentation

Full documentation available at [link]

## License

MIT License
```

## Step 13: Verify Setup

### Run Basic Checks

```bash
# Check Python version
python --version  # Should be 3.8+

# Check Django installation
python -c "import django; print(django.get_version())"

# Check DRF installation
python -c "import rest_framework; print(rest_framework.VERSION)"

# Run pre-commit
pre-commit run --all-files

# Check package can be imported
python -c "import django_permission_engine; print('OK')"
```

## Step 14: Initial Commit

```bash
# Add all files
git add .

# Initial commit
git commit -m "Initial project setup"

# Create initial branch for development
git checkout -b develop
```

## Checklist

- [ ] Project structure created
- [ ] Git repository initialized
- [ ] Virtual environment created and activated
- [ ] Requirements files created
- [ ] Dependencies installed
- [ ] setup.py configured
- [ ] pyproject.toml configured
- [ ] Package __init__.py created
- [ ] App config created
- [ ] Test settings configured
- [ ] Pre-commit hooks installed
- [ ] LICENSE file added
- [ ] README.md created
- [ ] Initial commit made

## Next Steps

Once setup is complete, proceed to **[02-database-models.md](02-database-models.md)** to implement the database models.
