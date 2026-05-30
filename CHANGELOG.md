# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-19

### Added
- Initial `.pln` reader extracted from pnfl-pdbtoexcel into a shared gameplan library.
- Gameplan writer and `profile_type` exposure from the J95 chunk.
- Typed `PlayRecord` subclasses with enums for play classification.
- Symmetric read/write `GamePlan` API with typed `Play` subtypes.
- Production-level PLN spec aligned with the code.
- `py.typed` marker and proper docstrings for the library API.
- MIT License.
- STATUS.md and TEST_STATUS.md documentation.
- Line-ending rules in .editorconfig.

### Changed
- Refactored `GamePlan` model with dependency injection and PascalCase naming.
- Strengthened `GamePlan` validation.
- Standardized project tooling config and package description.
- Fixed schema for stock plays; tests now use real `.pln` files.

### Removed
- `load_gameplan` alias and `special_flag` compatibility alias.

### Fixed
- S98 trailing byte: pad output to even (offense) or odd (defense) file length.
