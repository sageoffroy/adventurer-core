#!/usr/bin/env python3
"""Upgrade an installed Adventurer Core with the current client/core adapters."""

from __future__ import annotations

# Importing adventurer_apply installs the shared Item.dbc and 75% chassis
# adapters into the modules used by upgrade.py.  adventurer_apply only runs its
# CLI when executed directly, so importing it here is side-effect-limited to
# those package transforms.
import adventurer_apply  # noqa: F401
import upgrade


if __name__ == "__main__":
    raise SystemExit(upgrade.main())
