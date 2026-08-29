# mod-adventurer-gauntlet

Desafio de Khadgar para Aventureros de Azeroth.

## Diseno

- Los personajes comienzan la run en nivel 1.
- Khadgar registra al grupo y genera un nombre aleatorio con sabor a Warcraft.
- La expedicion encadena mazmorras originales de WoW.
- La muerte elimina a ese aventurero de la run.
- Los mobs normales no dan loot.
- Rares y bosses usan el sistema de recompensas del desafio.
- Los bosses entregan un Cofre de Expedicion con una pieza por aventurero vivo.
- El cofre no filtra clase ni spec: cualquier pieza compatible con el nivel puede salir.
- Las rarezas actuales son verde, azul y violeta; los pesos se configuran en `mod-adventurer-gauntlet.conf`.

## Flujo actual

- Khadgar dedicado: entry `910000`.
- Cofre de Expedicion: entry `910001`.
- Sima Ignea escala al nivel de la expedicion.
- Taragaman completa Sima Ignea y hace aparecer a Khadgar y al cofre.
- Khadgar castea el viaje a Minas de la Muerte cuando el lider decide continuar.
- El loot original del jefe final se reemplaza por el Cofre de Expedicion.

## Catalogo de objetos tempranos

La fuente editable es:

```text
data/items/early_items.csv
```

Cada fila crea un item custom en el rango reservado `911000-911999`. El item clona un `source_entry` stock para conservar modelo, icono, tipo de arma/armadura, sonidos y demas campos de WoW 3.3.5a. El CSV solo sobrescribe nombre, calidad, niveles, stats y los campos opcionales de armadura/dano.

Columnas de calidad aceptadas: `green`, `blue`, `purple` (tambien `verde`, `azul`, `violeta` o `2`, `3`, `4`).

Stats editables directamente por nombre:

```text
strength agility stamina intellect spirit
attack_power spell_power hit_rating crit_rating haste_rating
```

Los campos `armor`, `dmg_min1`, `dmg_max1` y `delay` son opcionales. Una celda vacia conserva el valor del objeto stock clonado, salvo los stats: los stats del source se limpian y se reemplazan por los definidos en la fila.

El instalador ejecuta:

```text
tools/khadgar_gauntlet/generate_items.py
```

y genera dentro del modulo instalado:

```text
data/sql/db-world/updates/2026_08_29_10_adventurer_gauntlet_items.generated.sql
```

Por lo tanto, para agregar o retocar objetos solo se edita `early_items.csv` y se vuelve a ejecutar el instalador antes de compilar/arrancar.

## Instalacion

```bash
CORE_DIR=~/aventurerosdeazeroth bash tools/khadgar_gauntlet/install.sh

cd ~/aventurerosdeazeroth/build
make -j2
make install
```

Durante desarrollo Khadgar puede spawnearse con:

```text
.npc add 910000
```
