# mod-adventurer-gauntlet

Primer corte instalable del Desafio de Khadgar para Aventureros de Azeroth.

## Diseno congelado

- Los personajes comienzan la run en nivel 1.
- Khadgar registra al grupo y genera un nombre aleatorio con sabor a Warcraft.
- La run futura encadenara mazmorras originales de WoW automaticamente.
- La muerte sera permanente para ese personaje dentro del modo.
- Los mobs normales no daran loot.
- Rares y bosses usaran el generador de recompensas del desafio.
- Los bosses entregaran un cofre con una cantidad de piezas igual a los aventureros vivos.
- Las piezas seran objetos existentes, escalados por nivel y con rareza verde/azul/violeta; legendarios se definiran aparte.
- El resultado final de cada run alimentara un ranking historico.

## Estado de este primer corte

Este incremento crea la base del modulo y el punto de entrada narrativo:

- configuracion propia;
- NPC Khadgar dedicado (entry `910000`), clonado del Khadgar stock sin modificar el original;
- gossip para aceptar el desafio;
- validacion de lider, grupo conectado, cantidad de jugadores, nivel inicial y estado vivo;
- generacion de nombre aleatorio de compania;
- registro temporal en memoria para todos los miembros del grupo.

Todavia no conecta la primera mazmorra ni persiste runs/ranking. Esas son las siguientes capas.

## Instalacion

Desde la rama `feature/khadgar-gauntlet-v1`:

```bash
CORE_DIR=~/aventurerosdeazeroth bash tools/khadgar_gauntlet/install.sh
```

Luego rerun de CMake, compilacion con `make -j2` y `make install`.

El SQL del modulo crea el template dedicado de Khadgar. El modulo no fija una ubicacion en el mundo todavia; durante desarrollo puede spawnearse con:

```text
.npc add 910000
```

Esto evita elegir una ubicacion definitiva antes de decidir donde vivira el hub del desafio.
