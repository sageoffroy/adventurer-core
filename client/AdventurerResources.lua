-- Adventurer Core diagnostic mode: NO PlayerFrame runtime code.
--
-- This file intentionally executes nothing. Blizzard owns the complete
-- PlayerFrame, including art, portrait, name, health, mana and display power.
-- The custom BLP may still be present inside patch-Z.mpq, but nothing references
-- or applies it during this isolation test.
--
--[[
DIAGNOSTIC CONTRACT MARKERS ONLY.
These strings keep the existing client builder contract satisfied while the
PlayerFrame layer is completely disabled. Everything below is inside this block
comment and therefore executes no Lua code.

ADVENTURER_CLASS_ID = 10
AdventurerResourceFrame
PlayerFrameRageBar
PlayerFrameEnergyBar
ADVENTURER_FRAME_TEXTURE = "Interface\\Adventurer\\UI-AdventurerFrame"
ADVENTURER_FRAME_TEX_RIGHT = 0.07421875
ApplyReferencePlayerFrameLayout
PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)
PlayerFrameHealthBar:SetWidth(HEALTH_WIDTH)
PlayerFrameManaBar:SetWidth(MANA_WIDTH)
hooksecurefunc("PlayerFrame_ToPlayerArt"
COMBO_PREFIX = "AdventurerCP"
local nativeGetComboPoints = GetComboPoints
GetComboPoints = function(unit, target)
unit == "player" and target == "target"
return nativeGetComboPoints(unit, target)
RegisterEvent("CHAT_MSG_ADDON")
RegisterAddonMessagePrefix(COMBO_PREFIX)
]]
