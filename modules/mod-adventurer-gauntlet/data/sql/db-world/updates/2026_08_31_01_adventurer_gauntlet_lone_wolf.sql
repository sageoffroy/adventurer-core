DELETE FROM `spell_dbc` WHERE `ID` = 910501;

INSERT INTO `spell_dbc` (
    `ID`,
    `DurationIndex`,
    `Effect_1`, `Effect_2`, `Effect_3`,
    `EffectBasePoints_1`, `EffectBasePoints_2`, `EffectBasePoints_3`,
    `ImplicitTargetA_1`, `ImplicitTargetA_2`, `ImplicitTargetA_3`,
    `EffectAura_1`, `EffectAura_2`, `EffectAura_3`,
    `SpellIconID`,
    `Name_Lang_enUS`, `Name_Lang_esES`, `Name_Lang_esMX`,
    `Description_Lang_enUS`, `Description_Lang_esES`, `Description_Lang_esMX`,
    `AuraDescription_Lang_enUS`, `AuraDescription_Lang_esES`, `AuraDescription_Lang_esMX`,
    `SchoolMask`
) VALUES (
    910501,
    21,
    6, 6, 6,
    19, 9, 9,
    1, 1, 1,
    31, 192, 216,
    910000,
    'Lone Wolf', 'Lobo solitario', 'Lobo solitario',
    '+20% damage dealt, +10% haste and +20% movement speed while facing Khadgar''s Challenge alone.',
    '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento mientras afrontas solo el Desafio de Khadgar.',
    '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento mientras afrontas solo el Desafio de Khadgar.',
    '+20% damage dealt, +10% haste and +20% movement speed.',
    '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento.',
    '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento.',
    1
);
