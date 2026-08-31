#!/usr/bin/env python3
"""SpellDraft v3 rank-tab entrypoint preserving the custom icon bundle."""

import icon_client
import spell_rank_tabs

icon_client.enable()

if __name__ == "__main__":
    raise SystemExit(spell_rank_tabs.main())
