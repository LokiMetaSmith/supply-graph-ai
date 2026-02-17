# Supply Graph AI Divergence Report

## Executive Summary

The local branch (`HEAD`) has significantly diverged from `upstream/main`. While both branches share a common ancestor, the development paths have separated considerably, resulting in a complex merge scenario.

**Merge Status:** **HIGH CONFLICT**
- **Conflicting Files:** ~248 files
- **Key Conflicts:** `src/core/main.py`, `src/cli/okh.py`, `src/core/matching/layers/base.py`
- **Data Conflicts:** Large number of conflicts in `synth/` vs `synthetic_data/` directories.

## API Changes

Both branches have introduced new API endpoints, which creates a direct conflict in `src/core/main.py` where routers are registered.

### Local Branch (HEAD)
- **New Endpoints:**
  - `/api/integration` (via `src/core/api/routes/integration.py`)
  - `/api/rfq` (via `src/core/api/routes/rfq.py`)
- **New Framework:**
  - `src/core/integration/` (Unified Integration Framework)
  - `src/core/integration/providers/` (GitHub, GitLab, SupplyChain)

### Upstream Branch
- **New Endpoints:**
  - `/api/convert`
  - `/api/taxonomy`
- **New Features:**
  - `demo/` directory with a Streamlit application (`app.py`, `rfq_generator.py`).
  - `.repo-map.md` significantly updated.

## Detailed Comparison

### Incoming Changes (Upstream -> Local)
**Commits:** ~29 new commits
**Key Changes:**
- **Documentation:** Extensive updates to `README.md` and `.repo-map.md`.
- **Demo:** Added a full `demo/` suite with `app.py`.
- **LLM:** Updates to `src/core/llm/providers/base.py`.
- **Infrastructure:** `.github/workflows` updates, `.env.local.example`.

### Outgoing Changes (Local -> Upstream)
**Commits:** ~9 new commits
**Key Changes:**
- **Scripts:** Added `scripts/bringup.sh` for development environment setup.
- **RFQ System:** Implemented generic RFQ system and documentation (`docs/features/rfq.md`).
- **Integration:** Implemented `IntegrationManager` and providers.
- **Infrastructure:** `docker-compose.llm.yml` added.

## Conflict Analysis

The merge dry-run identified approximately 248 conflicting files. The most critical conflicts are in:

1.  **`src/core/main.py`**:
    - Both branches added new router inclusions (`api_v1.include_router(...)`).
    - Upstream modified logging setup and storage initialization.
    - **Resolution Strategy:** Manual merge required to combine router registrations and keep upstream's logging/storage improvements.

2.  **`src/cli/okh.py`**:
    - Conflict in CLI command definitions.

3.  **Synthetic Data (`synth/` vs `synthetic_data/`)**:
    - Upstream likely renamed or heavily modified the synthetic data generation, leading to massive file conflicts.
    - **Resolution Strategy:** Determine which data set is authoritative (likely upstream's `synthetic_data/` if it's newer/renamed) and adopt it, porting any local changes if necessary.

## Recommendation

Merging `upstream/main` directly is risky and will require significant manual effort.

**Suggested Approach:**
1.  **Backup:** Create a backup branch of current work.
2.  **Cherry-Pick:**
    - Cherry-pick the `scripts/bringup.sh` and `docker-compose.llm.yml` as they are likely non-conflicting or easy to resolve.
    - Port the `src/core/integration` and `src/core/api/routes/{integration,rfq}.py` files manually.
3.  **Manual Merge of `main.py`**:
    - Apply upstream changes to `src/core/main.py`.
    - Re-add the `/api/integration` and `/api/rfq` router registrations.
4.  **Adopt Upstream Data:**
    - Accept upstream's `synthetic_data/` and `demo/` changes.
    - Verify if local `synth/` changes need to be migrated.
