-- Lobo solitario is authored in the installed Spell.dbc by the Gauntlet client
-- pipeline. Do not keep a sparse spell_dbc SQL override for the same ID because
-- AzerothCore loads spell_dbc on top of the file-backed DBC store and a partial
-- row can replace valid cloned metadata with zero/default values.
DELETE FROM `spell_dbc` WHERE `ID` = 910501;
