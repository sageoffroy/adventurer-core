#!/usr/bin/env python3
"""SpellDraft v3 entrypoint: existing Adventurer apply flow plus icon-pack support."""

import importlib
import sys
import types

# adventurer_apply establishes the existing Item.dbc, Tame and chassis adapters,
# but its final import of adventurer would otherwise snapshot client functions
# before the v3 icon adapter is enabled. Temporarily satisfy that import, then
# load the real front-end only after all client adapters are installed.
_placeholder = types.ModuleType("adventurer")
sys.modules["adventurer"] = _placeholder
import adventurer_apply  # noqa: E402
sys.modules.pop("adventurer", None)

import icon_client  # noqa: E402

icon_client.enable()
adventurer = importlib.import_module("adventurer")
adventurer_apply.adventurer = adventurer

if __name__ == "__main__":
    raise SystemExit(adventurer.main())
