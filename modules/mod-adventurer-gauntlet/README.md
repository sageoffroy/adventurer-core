# mod-adventurer-gauntlet

Desafio de Khadgar para Aventureros de Azeroth.

## Diseno congelado

- Los personajes comienzan la run en nivel 1.
- Khadgar registra al grupo y genera un nombre aleatorio con sabor a Warcraft.
- La run encadena mazmorras originales de WoW.
- La muerte sera permanente para ese personaje dentro del modo.
- Los mobs normales no dan loot.
- Rares y bosses usan el generador de recompensas del desafio.
- Los bosses entregan un Cofre de Expedicion con una cantidad de piezas igual a los aventureros vivos.
- El cofre usa equipo verde/azul/violeta apropiado al nivel sin filtrar clase ni spec.
- El resultado final de cada run alimentara un ranking historico.

## Catalogo de objetos

La fuente de verdad es:

`data/items/early_items.csv`

Cada fila crea un item custom dentro del rango `911000-911999` clonando un item stock de WotLK. Esto permite reutilizar modelos, iconos, slots, sonidos, materiales y durabilidad sin modificar DBC del cliente.

Campos especiales:

- `source_entry`: item stock que sirve como base. Para equipo curado conviene apuntar directamente a una pieza gris/blanca cuya apariencia queremos reutilizar.
- `display_id`: opcional. Si se completa, fuerza un `ItemDisplayInfo` stock distinto al del `source_entry`.
- `set_key`: opcional. Agrupa la pieza dentro de un set curado server-side.
- `equip_spell1` / `equip_spell2`: spells stock aplicados como efectos `Equip:` propios de esa pieza.
- stats, armor y dano pueden sobreescribirse sin cambiar el modelo.

Los efectos heredados del item fuente se limpian: un objeto nuevo solo conserva los efectos declarados explicitamente en el CSV.

El instalador genera automaticamente el SQL de `item_template`; no se edita SQL a mano.

## Sets curados

Los bonus estan en:

`data/items/sets.csv`

Formato:

`enabled;set_key;name;pieces_required;spell_id;description`

Una misma `set_key` puede tener varios umbrales, por ejemplo 2, 4 y 6 piezas. Los bonus se aplican server-side usando spells stock y se recalculan al entrar, equipar, desequipar o resucitar.

No se usa `item_template.itemset`: los sets nativos dependen de `ItemSet.dbc` y obligarian a parchear el cliente. Los sets del Gauntlet mantienen modelos e items 100% compatibles con el cliente stock; el texto descriptivo de los bonus puede declararse en el catalogo aunque no aparezca con el formato amarillo nativo de Blizzard.

### Ejemplo visual: Tejido pesado

La familia vendida por mercaderes de tela como Carla Granger puede usarse directamente como base de un set azul temprano:

- `837` Heavy Weave Armor - pecho
- `838` Heavy Weave Pants - piernas
- `839` Heavy Weave Gloves - manos
- `840` Heavy Weave Shoes - pies
- `3589` Heavy Weave Belt - cintura
- `3590` Heavy Weave Bracers - munecas

Cada pieza puede ser clonada con su propio `source_entry`, renombrada, convertida a calidad azul y asociada a la misma `set_key`.

## Instalacion

Desde la rama `feature/khadgar-gauntlet-v1`:

```bash
CORE_DIR=~/aventurerosdeazeroth bash tools/khadgar_gauntlet/install.sh
```

El instalador:

1. copia el modulo;
2. valida `early_items.csv`;
3. genera el SQL de items custom;
4. valida `sets.csv`;
5. genera las definiciones C++ de bonus de set.

Luego:

```bash
cd ~/aventurerosdeazeroth/build
make -j2
make install
```

Durante desarrollo Khadgar puede spawnearse con:

```text
.npc add 910000
```
