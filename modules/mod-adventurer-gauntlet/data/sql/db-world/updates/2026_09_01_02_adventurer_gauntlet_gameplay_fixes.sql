-- Adventurer Gauntlet: gameplay fixes found during the v3 in-game pass.

SET @LONE_WOLF := 910501;
SET @GAUNTLET_CHEST_ENTRY := 910001;

-- Spell.dbc remains the client/runtime presentation source, but AzerothCore's
-- server SpellMgr also needs the custom spell registered through spell_dbc.
-- Keep this row complete for the three aura effects used by Lobo solitario.
DELETE FROM `spell_dbc` WHERE `ID` = @LONE_WOLF;
INSERT INTO `spell_dbc`
(`ID`, `DurationIndex`,
 `Effect_1`, `Effect_2`, `Effect_3`,
 `EffectBasePoints_1`, `EffectBasePoints_2`, `EffectBasePoints_3`,
 `ImplicitTargetA_1`, `ImplicitTargetA_2`, `ImplicitTargetA_3`,
 `EffectAura_1`, `EffectAura_2`, `EffectAura_3`,
 `SpellIconID`,
 `SpellName_Lang_enUS`, `SpellName_Lang_esES`, `SpellName_Lang_esMX`,
 `SpellDescription_Lang_enUS`, `SpellDescription_Lang_esES`, `SpellDescription_Lang_esMX`,
 `SpellAuraDescription_Lang_enUS`, `SpellAuraDescription_Lang_esES`, `SpellAuraDescription_Lang_esMX`,
 `SchoolMask`)
VALUES
(@LONE_WOLF, 21,
 6, 6, 6,
 19, 9, 9,
 1, 1, 1,
 31, 192, 216,
 910000,
 'Lone Wolf', 'Lobo solitario', 'Lobo solitario',
 '+20% damage dealt, +10% haste and +20% movement speed while facing Khadgar''s Challenge alone.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento mientras afrontas solo el Desafío de Khadgar.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento mientras afrontas solo el Desafío de Khadgar.',
 '+20% damage dealt, +10% haste and +20% movement speed.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento.',
 1);

-- The cellar chest was visually intersecting the crate pile. Move only the
-- persistent Goldshire Gauntlet chest toward Khadgar and leave its Z/orientation.
UPDATE `gameobject`
SET `position_x` = -9472.2500,
    `position_y` = 5.5000000
WHERE `id` = @GAUNTLET_CHEST_ENTRY
  AND `map` = 0;
