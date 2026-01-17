"""
Setup configuration for django-permission-engine
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="django-permission-engine",
    version="0.1.3",
    description="Unified Permission Registry (UPR) for Django & DRF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sarthak",
    author_email="sarthaksnh5@gmail.com",
    url="https://github.com/sarthaksnh5/django_permission_engine",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "Django>=3.2",
        "djangorestframework>=3.12",
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
        "Source": "https://github.com/sarthaksnh5/django_permission_engine",
        "Tracker": "https://github.com/sarthaksnh5/django_permission_engine/issues",
    },
)
