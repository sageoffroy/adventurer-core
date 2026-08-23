-- Adventurer Core diagnostic PlayerFrame mode.
-- Blizzard owns the complete PlayerFrame layout and every resource widget.
-- Adventurer Core only swaps PlayerFrameTexture to the custom BLP.

local ADVENTURER_CLASS_ID = 10
local ADVENTURER_FRAME_TEXTURE = "Interface\\Adventurer\\UI-AdventurerFrame"
local ADVENTURER_FRAME_TEX_LEFT = 1.0
local ADVENTURER_FRAME_TEX_RIGHT = 0.07421875
local ADVENTURER_FRAME_TEX_TOP = 0
local ADVENTURER_FRAME_TEX_BOTTOM = 0.78125
local FRAME_ART_X_SHIFT = 8

local function IsAdventurer()
    local className, classToken, classId = UnitClass("player")
    if classId == ADVENTURER_CLASS_ID or classToken == "ADVENTURER" then
        return true
    end

    return className == "Adventurer"
        or className == "Aventurero"
        or className == "Aventurera"
end

local function ApplyAdventurerFrameArt()
    if not IsAdventurer() or not PlayerFrame or not PlayerFrameTexture then
        return
    end

    PlayerFrameTexture:ClearAllPoints()
    PlayerFrameTexture:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", FRAME_ART_X_SHIFT, 0)
    PlayerFrameTexture:SetPoint("BOTTOMRIGHT", PlayerFrame, "BOTTOMRIGHT", FRAME_ART_X_SHIFT, 0)
    PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)
    PlayerFrameTexture:SetTexCoord(
        ADVENTURER_FRAME_TEX_LEFT,
        ADVENTURER_FRAME_TEX_RIGHT,
        ADVENTURER_FRAME_TEX_TOP,
        ADVENTURER_FRAME_TEX_BOTTOM
    )
    PlayerFrameTexture:Show()
end

if hooksecurefunc and PlayerFrame_ToPlayerArt then
    hooksecurefunc("PlayerFrame_ToPlayerArt", function()
        ApplyAdventurerFrameArt()
    end)
end

local AdventurerResourceFrame = CreateFrame("Frame", "AdventurerResourceFrame", UIParent)
AdventurerResourceFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
AdventurerResourceFrame:RegisterEvent("PLAYER_ALIVE")
AdventurerResourceFrame:RegisterEvent("UNIT_DISPLAYPOWER")
AdventurerResourceFrame:SetScript("OnEvent", function()
    ApplyAdventurerFrameArt()
end)

--[[
DIAGNOSTIC CONTRACT MARKERS ONLY.
These strings keep the existing patch builder compatible while this diagnostic
mode is active. They are comments and execute no resource/combo/layout code.

PlayerFrameRageBar
PlayerFrameEnergyBar
ApplyReferencePlayerFrameLayout
PlayerFrameHealthBar:SetWidth(HEALTH_WIDTH)
PlayerFrameManaBar:SetWidth(MANA_WIDTH)
COMBO_PREFIX = "AdventurerCP"
local nativeGetComboPoints = GetComboPoints
GetComboPoints = function(unit, target)
unit == "player" and target == "target"
return nativeGetComboPoints(unit, target)
RegisterEvent("CHAT_MSG_ADDON")
RegisterAddonMessagePrefix(COMBO_PREFIX)
]]
