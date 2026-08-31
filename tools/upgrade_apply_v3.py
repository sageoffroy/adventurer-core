#!/usr/bin/env python3
"""SpellDraft v3 upgrade entrypoint using the existing updater plus icon support."""

# Reuse the v3 apply bootstrap solely for import ordering/adapter registration.
# It does not execute the apply CLI when imported.
import adventurer_apply_v3  # noqa: F401
import upgrade

if __name__ == "__main__":
    raise SystemExit(upgrade.main())
