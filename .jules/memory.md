## Archived: 2026-11-02

* Integration plugins implement lifecycle hooks: `initialize`, `register_routes`, `on_startup`, and `on_shutdown`.
* The `scripts/bringup.sh` script defines `--clean` as `docker-compose down -v` and `--reset` as a deep clean using `git clean -fdX` (removing ignored files like `.env` and `venv`).
* VCS providers return `ProjectData` objects in `IntegrationResponse` payloads.
* A plugin scaffold is available in `src/plugins/template/` to facilitate the creation of new integrations according to the project's standard structure.
* When testing FastAPI routes, `app.dependency_overrides` may fail; prefer patching the service class directly for robust mocking.
* LLM configurations are migrating from `LLMService` to the Unified Integration Framework.
* Local LLM services are defined in `docker-compose.llm.yml`, using the `ollama/ollama:latest` image on port 11434 with `llama3.1:8b` as the default model.
* The upstream repository is located at `https://github.com/helpfulengineering/supply-graph-ai`.
* The `OKHManifest` and `ManufacturingFacility` models include `provenance: Optional[str]` and `is_verified: bool` fields to support untrusted-by-default data ingestion.
* Tests for integrations are distributed across `tests/core/integration/`, `tests/core/api/`, and `tests/core/services/`.
* The core plugin framework (v0.1.0) distinguishes between two types of plugins: interop adapters (DataSourcePlugin for data normalization to OKH/OKW) and business-logic connectors.
* Sensitive credentials are managed by `SecretsManager` in `src/core/utils/secrets_manager.py`.
* Plugins must declare their capabilities (e.g., `NETWORK_EGRESS`, `STORAGE_READ`, `STORAGE_WRITE`) via an Enum in `BasePlugin` to support a least-privilege trust model.
* The project requires the Spacy model `en_core_web_sm` to be installed.
* Plugin routes must be registered via `PluginManager.register_all_routes(api_v1)` in `src/core/main.py` *after* core routers are included to avoid prefix/path conflicts. `discover_and_load()` must be called before registration.
* Setting `OHM_STRICT_PLUGINS=true` in the environment causes the application to fail hard if any plugin listed in `ACTIVE_PLUGINS` fails to load.
* OHM uses a modular plugin system defined in `src/plugins/base.py`, gated by the `ACTIVE_PLUGINS` list in `settings.py` (env `OHM_ACTIVE_PLUGINS`).
* Documentation for the `scripts/bringup.sh` utility is maintained in the `README.md` file under the 'Quick Start Script (Recommended)' section.
* Development scripts (e.g., `scripts/bringup.sh`) employ Python one-liners for file manipulation and network checks to ensure cross-platform compatibility (Linux, macOS, Windows Git Bash).
* Pydantic V2 migration: Use `model_config = ConfigDict(extra="ignore", env_file=".env")` instead of legacy `class Config` in models and settings.
* Directory structure conflict: Local repository uses `synth/` for data, whereas upstream uses `synthetic_data/`.
* UIF endpoints for provider discovery are at `/v1/api/integration/providers`.
* The project is built with Python 3.12 and FastAPI, using `uv` for dependency management.
* Architecture divergence: Local branch adds `/api/integration` and `/api/rfq`, while upstream adds `/api/convert` and `/api/taxonomy`, causing conflicts in router registration.
* For local LLM integration, `scripts/bringup.sh` dynamically sets `OLLAMA_BASE_URL` to `http://host.docker.internal:11434` for macOS/Windows and `http://172.17.0.1:11434` for Linux.
* The project utilizes a Unified Integration Framework (UIF) and a newer modular Plugin Architecture in `src/plugins/`.
* The `IntegrationManager` (for UIF) and `PluginManager` (for plugins) both implement singleton patterns with lifecycle management.
* API documentation for the Unified Integration Framework is in `docs/api/integration.md`.
* FastAPI Body parameters with Pydantic models should use `embed=True` in the `Body()` declaration if the client sends the model wrapped in a JSON key matching the parameter name.
* Feature documentation for the plugin system is in `docs/development/plugins.md`.
* The `.gitignore` file must not exclude the `tests/` directory.
* When testing HMAC signatures for JSON webhooks, use `json.dumps(payload, separators=(',', ':'))` to ensure the byte representation matches the compact serialization usually sent by clients.
* External integrations implement `BaseIntegrationProvider` or the newer `BasePlugin` architecture (including `DataSourcePlugin` for interop adapters).
* The local branch has diverged significantly from upstream `main`, causing ~248 file conflicts during merge attempts, particularly in `src/core/main.py` and `src/cli/okh.py`.
* The user prefers flag-driven CLI tools for development scripts, limiting interactive prompts to critical actions.
* The development environment is initialized via `scripts/bringup.sh`, which manages Docker orchestration and optional LLM integration with the `--with-llm` flag.
* The user requires a deep planning phase with explicit assumption confirmation via questions before any plan creation or code changes.
