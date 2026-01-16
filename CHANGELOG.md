# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release
- Permission registry engine
- Database models (Permission, Module, UserPermission)
- Declarative permission definitions with decorators
- DRF integration with PermissionRequired class
- Permission catalog API
- Management commands (upr_sync, upr_validate, upr_list)
- Comprehensive test suite
- Documentation

## [0.1.0] - 2024-01-15

### Added
- Core permission models
- Registry engine for permission synchronization
- Module and action decorators
- Runtime permission resolution
- DRF PermissionRequired class
- Permission catalog API endpoints
- Management commands for sync, validate, and list
- Test infrastructure and test suite
- Sphinx documentation setup

[Unreleased]: https://github.com/yourusername/django-permission-engine/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/django-permission-engine/releases/tag/v0.1.0
