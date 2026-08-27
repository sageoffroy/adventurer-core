# Darker Nights v1

Approved client-side lighting layer for WoW 3.3.5a.

This branch is intentionally isolated from Adventurer class, SpellDraft and talent work.

## Client patch ownership

Darker Nights must never modify or replace `patch-Z.MPQ`.

`patch-Z.MPQ` remains owned by the Adventurer / SpellDraft client pipeline and may change independently on other branches.

Darker Nights is packaged separately as:

`patch-Y.MPQ`

`patch-Y.MPQ` is reserved exclusively for Darker Nights in this project. The earlier experimental `patch-ZB.MPQ` name is retired and the installer disables it if found.

## Input

Stock `LightIntBand.dbc`, defaulting to:

`~/wow335-extract/dbc/LightIntBand.dbc`

## Generated files

Generated DBC:

`~/darker-nights-test/DBFilesClient/LightIntBand.dbc`

Installed client patch:

`<WoW>/Data/patch-Y.MPQ`

The generated DBC and MPQ are runtime artifacts and are not committed to Git.

## Approved lighting behavior

The final v1 modifies the first eight colour bands of each `LightIntBand.dbc` lighting profile:

- bands 0-1: general / ambient world lighting
- bands 2-6: sky and horizon layers
- band 7: distant/background fog used by far terrain such as mountains

This keeps foreground and distant terrain consistently dark while preserving enough sky colour for stars and moonlight.

### World / ambient curve

- 00:00: 15%
- 04:00: 15% — deep night remains flat until this point
- 06:00: 65%
- 08:00: 100%
- 18:00: 85%
- 20:00: 55%
- 22:00: 30%
- 24:00: 15%

### Sky curve

- 00:00: 30%
- 04:00: 30%
- 06:00: 70%
- 08:00: 100%
- 18:00: 90%
- 20:00: 65%
- 22:00: 40%
- 24:00: 30%

### Distant terrain / fog curve

- 00:00: 15%
- 04:00: 15%
- 06:00: 60%
- 08:00: 100%
- 18:00: 85%
- 20:00: 50%
- 22:00: 25%
- 24:00: 15%

The design rule is that midnight through 04:00 remains fully dark; dawn starts only after 04:00.

## Install / rebuild

Close WoW, then run:

```bash
bash tools/darker_nights/install.sh
```

The installer regenerates `LightIntBand.dbc`, builds `patch-Y.MPQ`, installs it into the WoW `Data` directory and backs up an existing `patch-Y.MPQ` before replacement.

## Server-side time

Darker Nights only controls how each time of day looks. The actual accelerated day/night clock is provided independently by the `mod-TimeIsTime` server module.
