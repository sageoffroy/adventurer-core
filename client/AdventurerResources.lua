-- Adventurer Core: universal resource HUD for the native class-10 Adventurer.
--
-- The server owns the actual pools. This file arranges Blizzard's native
-- PlayerFrame around the Adventurer frame art: Rage above Health, Mana below
-- Health, Energy below Mana, Runic Power vertically at the right, and native
-- Death Knight runes below the frame. Blizzard's native ComboFrame remains
-- attached to TargetFrame.

local ADVENTURER_CLASS_ID = 10
local POWER_RAGE = 1
local POWER_ENERGY = 3
local POWER_RUNIC_POWER = 6
local COMBO_PREFIX = "AdventurerCP"
local MAX_RUNES = 6

local ADVENTURER_FRAME_TEXTURE = "Interface\\Adventurer\\UI-AdventurerFrame"
local ADVENTURER_FRAME_WIDTH = 248
local ADVENTURER_FRAME_HEIGHT = 100
local ADVENTURER_FRAME_RIGHT_TEXCOORD = 0.03125

-- The source art is a 256x128 extension of Blizzard's UI-TargetingFrame atlas.
-- PlayerFrame renders that atlas horizontally flipped. Keeping a 1:1 source to
-- screen mapping preserves the stock frame exactly while exposing the new
-- 16-pixel strip on the rendered right side.
local BAR_LEFT = 106
local BAR_WIDTH = 119
local RAGE_TOP = 15
local RAGE_HEIGHT = 5
local HEALTH_TOP = 26
local HEALTH_HEIGHT = 13
local MANA_TOP = 45
local MANA_HEIGHT = 5
local ENERGY_TOP = 56
local ENERGY_HEIGHT = 6
local RUNIC_LEFT = 229
local RUNIC_TOP = 17
local RUNIC_WIDTH = 9
local RUNIC_HEIGHT = 40
local RUNES_LEFT = 104
local RUNES_TOP = 68

local function IsAdventurer()
    local className, classToken, classId = UnitClass("player")
    if classId == ADVENTURER_CLASS_ID or classToken == "ADVENTURER" then
        return true
    end

    -- The numeric class id is authoritative on normal 3.3.5a clients. Keep a
    -- localized-name fallback for clients whose UnitClass binding omits it.
    return className == "Adventurer"
        or className == "Aventurero"
        or className == "Aventurera"
end

local function GetPowerColor(powerId)
    if PowerBarColor and PowerBarColor[powerId] then
        local color = PowerBarColor[powerId]
        return color.r, color.g, color.b
    end

    if powerId == POWER_RAGE then
        return 1.0, 0.0, 0.0
    elseif powerId == POWER_ENERGY then
        return 1.0, 1.0, 0.0
    end

    return 0.0, 0.82, 1.0
end

local function CreateResourceBar(name, powerId)
    local bar = CreateFrame("StatusBar", name, UIParent)
    bar.powerId = powerId
    bar:SetStatusBarTexture("Interface\\TargetingFrame\\UI-StatusBar")
    bar:SetFrameStrata("LOW")

    local r, g, b = GetPowerColor(powerId)
    bar:SetStatusBarColor(r, g, b)

    local background = bar:CreateTexture(nil, "BACKGROUND")
    background:SetAllPoints(bar)
    background:SetTexture("Interface\\TargetingFrame\\UI-StatusBar")
    background:SetVertexColor(0.08, 0.08, 0.08, 0.85)

    bar:Hide()
    return bar
end

local rageBar = CreateResourceBar("AdventurerRageBar", POWER_RAGE)
local energyBar = CreateResourceBar("AdventurerEnergyBar", POWER_ENERGY)
local runicBar = CreateResourceBar("AdventurerRunicPowerBar", POWER_RUNIC_POWER)

local function UpdateBar(bar)
    local current = UnitPower("player", bar.powerId) or 0
    local maximum = UnitPowerMax("player", bar.powerId) or 0

    if maximum <= 0 then
        maximum = 1
    end

    bar:SetMinMaxValues(0, maximum)
    bar:SetValue(current)
end

local function ApplyAdventurerPlayerFrameArt()
    if not PlayerFrame or not PlayerFrameTexture then
        return
    end

    PlayerFrameTexture:ClearAllPoints()
    PlayerFrameTexture:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", 0, 0)
    PlayerFrameTexture:SetWidth(ADVENTURER_FRAME_WIDTH)
    PlayerFrameTexture:SetHeight(ADVENTURER_FRAME_HEIGHT)
    PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)
    PlayerFrameTexture:SetTexCoord(
        1.0,
        ADVENTURER_FRAME_RIGHT_TEXCOORD,
        0,
        0.78125
    )
end

local function PositionNativeBars()
    if not PlayerFrame or not PlayerFrameHealthBar or not PlayerFrameManaBar then
        return
    end

    PlayerFrameHealthBar:ClearAllPoints()
    PlayerFrameHealthBar:SetPoint(
        "TOPLEFT",
        PlayerFrame,
        "TOPLEFT",
        BAR_LEFT,
        -HEALTH_TOP
    )
    PlayerFrameHealthBar:SetWidth(BAR_WIDTH)
    PlayerFrameHealthBar:SetHeight(HEALTH_HEIGHT)

    PlayerFrameManaBar:ClearAllPoints()
    PlayerFrameManaBar:SetPoint(
        "TOPLEFT",
        PlayerFrame,
        "TOPLEFT",
        BAR_LEFT,
        -MANA_TOP
    )
    PlayerFrameManaBar:SetWidth(BAR_WIDTH)
    PlayerFrameManaBar:SetHeight(MANA_HEIGHT)
end

local function PositionAuxiliaryBars()
    if not PlayerFrame then
        return
    end

    rageBar:ClearAllPoints()
    rageBar:SetOrientation("HORIZONTAL")
    rageBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", BAR_LEFT, -RAGE_TOP)
    rageBar:SetWidth(BAR_WIDTH)
    rageBar:SetHeight(RAGE_HEIGHT)

    energyBar:ClearAllPoints()
    energyBar:SetOrientation("HORIZONTAL")
    energyBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", BAR_LEFT, -ENERGY_TOP)
    energyBar:SetWidth(BAR_WIDTH)
    energyBar:SetHeight(ENERGY_HEIGHT)

    runicBar:ClearAllPoints()
    runicBar:SetOrientation("VERTICAL")
    runicBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", RUNIC_LEFT, -RUNIC_TOP)
    runicBar:SetWidth(RUNIC_WIDTH)
    runicBar:SetHeight(RUNIC_HEIGHT)
end

local function PositionBars()
    ApplyAdventurerPlayerFrameArt()
    PositionNativeBars()
    PositionAuxiliaryBars()
end

local function RefreshRunes()
    if not RuneFrame or not PlayerFrame then
        return
    end

    RuneFrame:ClearAllPoints()
    RuneFrame:SetScale(0.85)
    RuneFrame:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", RUNES_LEFT, -RUNES_TOP)
    RuneFrame:Show()

    if RuneButton_Update then
        for index = 1, MAX_RUNES do
            local button = _G["RuneButtonIndividual" .. index]
            if button then
                RuneButton_Update(button, button:GetID(), true)
            end
        end
    end
end

local function HideAdventurerResources()
    rageBar:Hide()
    energyBar:Hide()
    runicBar:Hide()

    if RuneFrame then
        RuneFrame:Hide()
    end
end

local function PlayerIsUsingVehicleUI()
    return UnitHasVehicleUI and UnitHasVehicleUI("player")
end

-- ---------------------------------------------------------------------------
-- Combo points
-- ---------------------------------------------------------------------------
-- The 3.3.5a client deliberately returns zero from GetComboPoints for classes
-- other than Rogue/Druid. AzerothCore still tracks combo points for Adventurer,
-- so the server mirrors the visible count through AdventurerCP. We only replace
-- the player->target query used by Blizzard's own ComboFrame; every other call
-- continues to use the original API.
local nativeGetComboPoints = GetComboPoints
local adventurerComboPoints = 0

GetComboPoints = function(unit, target)
    if IsAdventurer() and unit == "player" and target == "target" then
        return adventurerComboPoints
    end
    return nativeGetComboPoints(unit, target)
end

local function SetVisibleComboPoints(points)
    adventurerComboPoints = tonumber(points) or 0
    if adventurerComboPoints < 0 then
        adventurerComboPoints = 0
    elseif adventurerComboPoints > 5 then
        adventurerComboPoints = 5
    end

    if ComboFrame_Update then
        ComboFrame_Update()
    end
end

-- ---------------------------------------------------------------------------
-- Rune usability
-- ---------------------------------------------------------------------------
-- RuneFrame polls GetRuneCooldown itself, so its cooldown sweep can finish even
-- when the action bar never receives ACTIONBAR_UPDATE_USABLE for class 10. The
-- server now sends the native SMSG_ADD_RUNE_POWER transition when a rune becomes
-- ready; this small refresh keeps Blizzard's buttons visually in lockstep with
-- the native client cache after that packet arrives.
local lastRuneReadyMask = -1

local function GetRuneReadyMask()
    local mask = 0
    for index = 1, MAX_RUNES do
        local _, _, ready = GetRuneCooldown(index)
        if ready then
            mask = mask + (2 ^ (index - 1))
        end
    end
    return mask
end

local actionButtonPrefixes = {
    "ActionButton",
    "MultiBarBottomLeftButton",
    "MultiBarBottomRightButton",
    "MultiBarRightButton",
    "MultiBarLeftButton",
    "BonusActionButton",
}

local function RefreshActionButtonUsability()
    if not ActionButton_UpdateUsable then
        return
    end

    for _, prefix in ipairs(actionButtonPrefixes) do
        for index = 1, 12 do
            local button = _G[prefix .. index]
            if button and button.action and HasAction(button.action) then
                ActionButton_UpdateUsable(button)
            end
        end
    end
end

local function RefreshRuneActionUsability()
    local mask = GetRuneReadyMask()
    if mask == lastRuneReadyMask then
        return
    end

    lastRuneReadyMask = mask
    RefreshActionButtonUsability()
end

local function RefreshAdventurerResources()
    if not IsAdventurer() then
        return
    end

    if PlayerIsUsingVehicleUI() then
        HideAdventurerResources()
        return
    end

    PositionBars()
    UpdateBar(rageBar)
    UpdateBar(energyBar)
    UpdateBar(runicBar)

    rageBar:Show()
    energyBar:Show()
    runicBar:Show()
    RefreshRunes()
    RefreshRuneActionUsability()

    if ComboFrame_Update then
        ComboFrame_Update()
    end
end

local AdventurerResourceFrame = CreateFrame("Frame", "AdventurerResourceFrame", UIParent)
AdventurerResourceFrame.elapsed = 0
AdventurerResourceFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
AdventurerResourceFrame:RegisterEvent("PLAYER_ALIVE")
AdventurerResourceFrame:RegisterEvent("UNIT_DISPLAYPOWER")
AdventurerResourceFrame:RegisterEvent("UNIT_ENTERED_VEHICLE")
AdventurerResourceFrame:RegisterEvent("UNIT_EXITED_VEHICLE")
AdventurerResourceFrame:RegisterEvent("PLAYER_TARGET_CHANGED")
AdventurerResourceFrame:RegisterEvent("CHAT_MSG_ADDON")
AdventurerResourceFrame:RegisterEvent("RUNE_POWER_UPDATE")

AdventurerResourceFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if IsAdventurer() and prefix == COMBO_PREFIX then
            SetVisibleComboPoints(message)
        end
        return
    end

    if event == "PLAYER_ENTERING_WORLD" then
        if RegisterAddonMessagePrefix then
            RegisterAddonMessagePrefix(COMBO_PREFIX)
        end
        SetVisibleComboPoints(0)
        lastRuneReadyMask = -1
    elseif event == "PLAYER_TARGET_CHANGED" then
        -- Hide stale points immediately; the server sends the correct count for
        -- the new selected target on its next 100 ms sync tick.
        SetVisibleComboPoints(0)
    elseif event == "RUNE_POWER_UPDATE" then
        RefreshRuneActionUsability()
    else
        local unit = ...
        if unit and unit ~= "player" then
            return
        end
    end

    RefreshAdventurerResources()
end)

AdventurerResourceFrame:SetScript("OnUpdate", function(self, elapsed)
    if not IsAdventurer() then
        return
    end

    self.elapsed = self.elapsed + elapsed
    if self.elapsed < 0.10 then
        return
    end
    self.elapsed = 0

    if PlayerIsUsingVehicleUI() then
        HideAdventurerResources()
        return
    end

    UpdateBar(rageBar)
    UpdateBar(energyBar)
    UpdateBar(runicBar)

    -- Blizzard may reassert PlayerFrame dimensions or anchors after state
    -- changes. Reapply only the Adventurer player's local layout every tick.
    PositionBars()
    RefreshRuneActionUsability()

    if not rageBar:IsShown() then
        rageBar:Show()
        energyBar:Show()
        runicBar:Show()
    end
    if RuneFrame and not RuneFrame:IsShown() then
        RefreshRunes()
    end
end)
