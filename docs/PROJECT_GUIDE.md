# Aventureros de Azeroth — project guide

This is the structural source of truth for the repository. Its purpose is to let a developer or a new AI session understand what each important directory/file does and how the main flows connect before changing code.

Read `AI_CONTEXT.md` first for working rules. For SpellDraft internals read `SPELLDRAFT.md`. For adapting a spell read `SPELL_WORKFLOW.md`. For dungeon/Gauntlet work read `GAUNTLET.md` and `modules/mod-adventurer-gauntlet/README.md`.

## Product layers and stable branches

Aventureros de Azeroth has two technical layers in this repository:

```text
stable/spelldraft-v2
  = native Adventurer class + SpellDraft v2

stable/gauntlet-v2
  = stable/spelldraft-v2 + mod-adventurer-gauntlet
```

The dependency direction is one-way: Gauntlet depends on the matching stable SpellDraft major version; SpellDraft does not depend on Gauntlet.

Gauntlet-only evolution may advance as `v2.1`, `v2.2`, etc. When the stable SpellDraft base becomes v3, integrate that base into Gauntlet and continue as `stable/gauntlet-v3`.

Old `feature/khadgar-gauntlet-*` branches and `aventurerosdeazeroth/feature/mod-dungeon-master` are historical development references only.

## Repository map

### Root entrypoints

- `apply.sh` — clean Adventurer/SpellDraft installation entrypoint. Coordinates preflight, source patching, DB/DBC/client/runtime installation and transaction state.
- `update.sh` — updates an existing Adventurer installation using the same pipeline and preserves editable runtime files where supported.
- `rollback.sh` — reverses Adventurer-owned installation state using the repository's current rollback mechanism.
- `preflight.sh` — read-only compatibility/preflight entrypoint.
- `verify.sh` — verification entrypoint for the installed state.
- `README.md` — short human entrypoint; it points to the current architecture documents instead of duplicating them.

Gauntlet is installed after the normal Adventurer/SpellDraft update/apply flow through `tools/khadgar_gauntlet/install.sh`.

### `config/`

Configuration and source data consumed by build/install/runtime tooling.

#### `config/spelldraft/`

- `cards.csv` — packaged SpellDraft card catalogue. Defines cards, types, source levels, rarities, weights, rank grants and dependency metadata.
- `catalog_metadata.csv` — additional catalogue metadata used by current SpellDraft generation/relationships.
- `spelldraft.conf` — packaged editable runtime configuration seed for SpellDraft balance/meta settings.
- `subclasses.json` — presentation-subclass metadata used by current SpellDraft/subclass tooling.

#### `config/playerbots/`

- `managed.conf` — Adventurer-managed Playerbots profile used when Playerbots integration is present.

### `client/`

Client-side source material installed into the WotLK client by the existing client pipeline.

- `AdventurerCollections.lua` — client-side collection/talent-book presentation logic.
- `AdventurerDraftMeta.lua` — SpellDraft draft/meta UI behavior and addon-protocol handling.
- `AdventurerPlayerFrame.xml` — FrameXML layout/registration for Adventurer-specific player UI pieces.
- `AdventurerResources.lua` — client display logic for Adventurer resources.
- `art/` — client art assets owned by the project.
- `baseline/CharacterCreate.lua` — baseline Blizzard client file used by the patching process for character-creation changes.
- `baseline/FrameXML.toc` — baseline client TOC used by the client patch process.

### `payload/`

Files that Adventurer owns and installs into the target AzerothCore tree rather than editing as native upstream files.

#### `payload/core/src/server/scripts/Custom/`

- `adventurer_core.cpp` — main custom server runtime for the native Adventurer class and core Adventurer gameplay integration.
- `adventurer_collections.cpp` — server-side collection/talent-book support and related Adventurer addon communication.

### `modules/mod-adventurer-gauntlet/`

Server-side Gauntlet / Dungeon Master module. This directory is intentionally separate from SpellDraft gameplay code.

- `src/AdventurerGauntlet.cpp` — main dungeon-run orchestration and mode behavior.
- `src/GauntletScaling.cpp` — Gauntlet creature/group scaling.
- `src/GauntletPermadeath.cpp` — permanent-death/run-death behavior.
- `src/CuratedRewards.cpp` — controlled boss rewards. Current Ragefire rewards are written directly to boss corpse loot.
- `src/AccountStash.cpp` — persistent account stash behavior.
- `src/SetBonuses.cpp` — custom Gauntlet set-bonus handling.
- `src/KhadgarCelebration.cpp` — Khadgar-related presentation/celebration behavior.
- `src/loader.h` — module script registration.
- `conf/` — Gauntlet runtime configuration distribution.
- `data/items/early_items.csv` — curated/custom reward item catalogue.
- `data/items/sets.csv` — Gauntlet set definitions.
- `data/sql/` — Gauntlet-owned world/characters database updates.
- `README.md` — module-specific behavior/install notes; it must agree with `docs/GAUNTLET.md`.

### `sql/`

World database changes owned by the Adventurer/SpellDraft base.

#### `sql/world/`

- `001_adventurer.sql` — foundational Adventurer world rows.
- `003_adventurer_chassis.sql` — later chassis/world-data adjustments.
- `005_adventurer_chassis_80.sql` — level-80-era chassis/world-data adjustments.

Gauntlet-specific SQL belongs under `modules/mod-adventurer-gauntlet/data/sql/`, not here.

### `tools/`

Python implementation behind the shell entrypoints.

- `adventurer.py` — common installer/orchestration utilities, target validation, transaction/state helpers and shared filesystem logic.
- `adventurer_apply.py` — Adventurer apply wrapper and narrow project-specific native transforms, including the SpellDraft Tame Beast class gate.
- `adopt_source.py` — explicitly adopts approved pre-existing native source files into the installer ownership/rollback state when a stable update begins owning them.
- `core_patch.py` — exact-anchor transformations applied to native AzerothCore source files.
- `database.py` — database install/snapshot/restore support used by the current pipeline.
- `dbc.py` — core DBC transformation/staging/install logic for Adventurer.
- `client.py` — builds/installs the Adventurer client patch and related client files/DBCs.
- `mpq.py` — MPQ/client archive support used by the client pipeline.
- `package_rollback.py` — packaging/support for the repository's existing rollback state.
- `upgrade.py` — update flow for an existing Adventurer installation, including current ownership/state handling.
- `spelldraft_runtime.py` — packaged/runtime SpellDraft catalogue and configuration handling.
- `spell_rank_tabs.py` — generation/handling related to SpellDraft spell ranks/tabs and associated client/server data.
- `subclasses.py` — generation/handling of the four SpellDraft presentation subclasses and their metadata.
- `talents.py` — current talent-related generation/helper logic used by the project.
- `sync_item_dbc.py` — shared final Item.dbc synchronization point used by the Adventurer client/server bundle and Gauntlet custom equipment integration.
- `playerbots_runtime.py` — runtime Playerbots compatibility/profile integration.
- `playerbots_source_patch.py` — source compatibility changes needed when Playerbots is present.
- `test_characters.py` — utilities for project test-character setup/management; despite the name this is tooling, not the automated `tests/` suite.
- `world.py` — world/data orchestration used by the installer.
- `chassis_audit.py` — existing audit helper for the Adventurer chassis.
- `check_cpp_syntax.py` — lightweight existing C++ syntax/shape helper.

#### `tools/khadgar_gauntlet/`

Gauntlet-specific installation, generation and client tooling.

- `install.sh` — installs/updates the Gauntlet module into the target AzerothCore checkout.
- `AdventurerGauntletStash.lua` — Gauntlet stash client UI/runtime integration.
- `AdventurerMinimapFix.lua` — Gauntlet client minimap compatibility fix.
- `build_catalog.py` — builds/normalizes Gauntlet reward catalogue data.
- `generate_items.py` — generates custom Gauntlet item data.
- `generate_sets.py` — generates custom Gauntlet set definitions/server include data.
- `patch_item_dbc.py` — Gauntlet item DBC helper.
- `patch_spell_dbc.py` — Gauntlet spell DBC helper where required by module content.

The directory keeps the historical `khadgar_gauntlet` name to avoid needless path churn. Khadgar is only one part of the Gauntlet module.

### `tests/`

Large automated test suite accumulated during development. It is not the architectural source of truth and it is not the default place to start a gameplay change.

Project policy is documented in `AI_CONTEXT.md`: do not add tests by default, and do not enlarge a feature merely to satisfy stale implementation-detail tests. The primary gameplay validation loop is apply/update, compile/start when required, and in-game testing.

### `docs/`

Current documentation sources:

- `AI_CONTEXT.md` — durable working rules and branch model for new AI/developer sessions.
- `PROJECT_GUIDE.md` — this repository map and flow reference.
- `SPELLDRAFT.md` — current Adventurer/SpellDraft model.
- `SPELL_WORKFLOW.md` — operational spell-adaptation process.
- `GAUNTLET.md` — Gauntlet boundaries, versioning and install/update flow.
- `ROLLBACK.md` — detailed current rollback behavior.
- `ARCHITECTURE.md` — compatibility pointer to this guide plus Gauntlet documentation.

## Main flows

### 1. Clean Adventurer / SpellDraft installation

```text
apply.sh
  -> common argument/target validation
  -> preflight of required native source/data shapes
  -> stage Adventurer-owned source + native core transformations
  -> stage/apply world database changes
  -> build/stage server DBC changes
  -> install SpellDraft runtime/config/catalogue
  -> build/install client patch + client DBC/files
  -> optional Playerbots integration when present
  -> record current installer state for verify/update/rollback
```

The installer does not compile worldserver. If native C++ changed, compile/install worldserver separately and restart it.

### 2. Update existing Adventurer / SpellDraft installation

```text
update.sh
  -> inspect existing Adventurer state
  -> adopt explicitly approved newly-owned native source when required
  -> plan current source/data changes
  -> apply the existing upgrade/ownership rules
  -> refresh packaged runtime defaults while preserving editable runtime copies where supported
  -> update server DBC/client payload
  -> update transaction/install state
```

### 3. Gauntlet install/update

```text
checkout stable/gauntlet-vN
  -> run normal Adventurer update/apply for the matching SpellDraft base
  -> tools/khadgar_gauntlet/install.sh
  -> copy/install mod-adventurer-gauntlet
  -> generate/install Gauntlet items/sets/client pieces
  -> shared final Item.dbc synchronization where required
  -> make -j2 && make install
  -> start worldserver
  -> test the dungeon flow in game
```

Gauntlet-only fixes stay on the Gauntlet line. Do not merge them back into SpellDraft unless the change is genuinely a base Adventurer/SpellDraft change.

### 4. Native core C++ change

```text
requested gameplay behavior
  -> prove that data/DBC/runtime cannot express it
  -> identify exact AzerothCore native file
  -> add the smallest transformation to the existing native patch path
  -> apply/update
  -> rebuild worldserver
  -> start server
  -> test behavior in game
```

Do not create a second patcher.

### 5. DBC/client data change

```text
source config/catalogue
  -> tools/dbc.py and/or existing generator
  -> staged server DBC
  -> tools/client.py client payload
  -> same intended DBC/game data reaches server and client where required
  -> restart client/server as required
  -> test in game
```

DBC edits to native spell IDs may be global. Do not assume an edit is Adventurer-private unless the implementation actually creates/uses a private copy.

### 6. SpellDraft runtime flow

```text
config/spelldraft/cards.csv + spelldraft.conf + metadata
  -> packaged/runtime processing in tools/spelldraft_runtime.py
  -> server-side Adventurer/SpellDraft runtime
  -> persisted per-character draft state
  -> addon messages to client
  -> client/AdventurerDraftMeta.lua renders offers/meta actions
  -> selected card teaches/progresses configured spell/talent grants
```

See `SPELLDRAFT.md` for current progression and meta mechanics.

### 7. Spell adaptation flow

```text
existing native spell + desired Adventurer behavior
  -> cards.csv/catalogue entry
  -> inspect closest existing adaptation
  -> DBC/data adaptation if sufficient
  -> native core transform only when native runtime logic is required
  -> client tooltip/data update only when the client must display changed behavior
  -> apply/update
  -> rebuild/restart if C++ changed
  -> in-game validation
```

See `SPELL_WORKFLOW.md`.

### 8. Playerbots flow

```text
installer detects modules/mod-playerbots
  -> playerbots_source_patch.py applies required source compatibility
  -> playerbots_runtime.py / config/playerbots/managed.conf apply managed behavior
  -> if module absent, integration is skipped
```

Playerbots is optional and must not become a requirement for core Adventurer installation.

### 9. Rollback flow

```text
rollback.sh
  -> inspect recorded Adventurer installation state
  -> verify current rollback preconditions
  -> restore database/file/DBC/client state through existing rollback tooling
  -> remove Adventurer transaction/install state when successful
```

Detailed safeguards and exact DB behavior live in `ROLLBACK.md`. Gameplay work should not add new rollback layers by default.

### 10. Normal gameplay validation

```text
make minimal change
  -> apply.sh/update.sh and Gauntlet installer when applicable
  -> compile/install worldserver only if required
  -> restart server/client as required
  -> test the actual feature in game
  -> fix observed failure
```

Automated tests may be useful for a specific recurring failure, but they are not the default definition of done for this project.

## Documentation rule

When architecture or branch/version relationships change, update this guide and the relevant focused document. When SpellDraft rules change, update `SPELLDRAFT.md`. When Gauntlet rules or installation change, update `GAUNTLET.md` and the module README. Avoid creating Markdown files for temporary experiments; Git history already preserves development history.
