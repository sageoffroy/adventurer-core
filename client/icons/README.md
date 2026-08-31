# SpellDraft v3 icon pack

Copy the custom `.blp` icon pack into this directory before running the normal Adventurer installer/update flow.

- Files are packaged into `patch-Z.mpq` under `Interface\\Icons\\`.
- A file whose name/path matches a Blizzard icon overrides that icon globally in the client.
- Every packaged icon also receives a stable Adventurer `SpellIcon.dbc` ID from `client/icons/catalog.csv`, so additional icons can be referenced by custom spells.
- Keep the catalog committed once the pack has been imported; IDs must not be regenerated casually after spells begin referencing them.

Run this once after copying/changing the pack:

```bash
python3 tools/icon_pack.py catalog
```

The command scans this directory recursively, ignores this README/catalog, and assigns IDs beginning at 910000 while preserving IDs already present in the catalog.
