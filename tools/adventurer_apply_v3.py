#!/usr/bin/env python3
"""SpellDraft v3 entrypoint: existing Adventurer apply flow plus icon-pack support."""

import adventurer_apply
import icon_client

icon_client.enable()

if __name__ == "__main__":
    raise SystemExit(adventurer_apply.adventurer.main())
