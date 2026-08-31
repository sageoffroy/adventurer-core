#!/usr/bin/env python3
"""SpellDraft v3 upgrade entrypoint using the existing updater plus icon support."""

import adventurer_apply  # installs existing Item.dbc/Tame/chassis adapters
import icon_client

icon_client.enable()

import upgrade  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(upgrade.main())
