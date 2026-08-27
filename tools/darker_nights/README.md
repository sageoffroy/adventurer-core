# Darker Nights v1

Experimental client-side lighting layer for WoW 3.3.5a.

This branch is intentionally isolated from Adventurer class, SpellDraft and talent work.

## Client patch ownership

Darker Nights must never modify or replace `patch-Z.MPQ`.

`patch-Z.MPQ` remains owned by the Adventurer / SpellDraft client pipeline and may change independently on other branches.

Darker Nights is packaged separately as:

`patch-Y.MPQ`

`patch-Y.MPQ` is reserved exclusively for Darker Nights in this project. The earlier experimental `patch-ZB.MPQ` name is retired and the installer disables it if found.

This lets the lighting layer be enabled, disabled and iterated without coupling it to Adventurer, SpellDraft, talents or other client changes.

## Input

Stock `LightIntBand.dbc`, defaulting to:

`~/wow335-extract/dbc/LightIntBand.dbc`

## Output

`~/darker-nights-test/DBFilesClient/LightIntBand.dbc`

## Scope of v1

Only the first two LightIntBand color bands are modified for the initial visual test: global diffuse and global ambient light. Sky, fog, sun, clouds and water are left untouched.

Initial brightness curve:

- 00:00: 25%
- 04:00: 30%
- 06:00: 65%
- 08:00: 100%
- 18:00: 85%
- 20:00: 55%
- 22:00: 35%
- 24:00: 25%

The curve is deliberately strong so the first in-game test can clearly show whether the approach produces the desired night effect.

## Build

```bash
bash tools/darker_nights/build.sh
```

The generated DBC is not committed to Git. The client artifact for this feature is always `patch-Y.MPQ`, never `patch-Z.MPQ`.
