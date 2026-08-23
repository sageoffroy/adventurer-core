-- Adventurer Core: universal resource HUD for the native class-10 Adventurer.
--
-- The server owns the actual pools. This file arranges Blizzard's native
-- PlayerFrame around the Adventurer frame art: Rage above Health, Mana below
-- Health, and Energy below Mana. Blizzard's native ComboFrame remains attached
-- to TargetFrame.

local ADVENTURER_CLASS_ID = 10
local POWER_RAGE = 1
local POWER_ENERGY = 3
local COMBO_PREFIX = "AdventurerCP"

local locale = GetLocale()
local labels
if locale == "esES" or locale == "esMX" then
    labels = {
        [POWER_RAGE] = "Ira",
        [POWER_ENERGY] = "Energía",
    }
else
    labels = {
        [POWER_RAGE] = "Rage",
        [POWER_ENERGY] = "Energy",
    }
end

local ADVENTURER_FRAME_TEXTURE = "Interface\\Adventurer\\UI-AdventurerFrame"
local ADVENTURER_FRAME_WIDTH = 248
local ADVENTURER_FRAME_HEIGHT = 100
local ADVENTURER_FRAME_RIGHT_TEXCOORD = 0.03125

-- All resource bars stay behind the painted shell. Blizzard's level text lives
-- on PlayerFrame, so we mirror it on the HIGH-strata overlay to keep it visible.
local BAR_LEFT = 110
local BAR_WIDTH = 115
local RAGE_LEFT = 91
local RAGE_WIDTH = 135
local RAGE_TOP = 12
local RAGE_HEIGHT = 10
local HEALTH_TOP = 26
local HEALTH_HEIGHT = 13
local MANA_TOP = 45
local MANA_HEIGHT = 5
local ENERGY_TOP = 56
local ENERGY_HEIGHT = 6

local function IsAdventurer()
    local className, classToken, classId = UnitClass("player")
    if classId == ADVENTURER_CLASS_ID or classToken == "ADVENTURER" then
        return true
    end

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
    bar:SetFrameStrata("BACKGROUND")
    bar:SetFrameLevel(1)
    bar:EnableMouse(true)

    local r, g, b = GetPowerColor(powerId)
    bar:SetStatusBarColor(r, g, b)

    local background = bar:CreateTexture(nil, "BACKGROUND")
    background:SetAllPoints(bar)
    background:SetTexture("Interface\\TargetingFrame\\UI-StatusBar")
    background:SetVertexColor(0.08, 0.08, 0.08, 0.85)

    local value = bar:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    value:SetPoint("CENTER", bar, "CENTER", 0, 0)
    value:SetJustifyH("CENTER")
    value:Hide()
    bar.valueText = value

    bar:SetScript("OnEnter", function(self)
        self.valueText:Show()
    end)
    bar:SetScript("OnLeave", function(self)
        self.valueText:Hide()
    end)

    bar:Hide()
    return bar
end

local rageBar = CreateResourceBar("AdventurerRageBar", POWER_RAGE)
local energyBar = CreateResourceBar("AdventurerEnergyBar", POWER_ENERGY)

local frameArtOverlay = CreateFrame("Frame", "AdventurerPlayerFrameArtOverlay", UIParent)
frameArtOverlay:SetWidth(ADVENTURER_FRAME_WIDTH)
frameArtOverlay:SetHeight(ADVENTURER_FRAME_HEIGHT)
frameArtOverlay:SetFrameStrata("HIGH")
frameArtOverlay:SetFrameLevel(1)
frameArtOverlay:EnableMouse(false)
frameArtOverlay:Hide()

local frameArtTexture = frameArtOverlay:CreateTexture(nil, "ARTWORK")
frameArtTexture:SetAllPoints(frameArtOverlay)
frameArtTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)
frameArtTexture:SetTexCoord(
    1.0,
    ADVENTURER_FRAME_RIGHT_TEXCOORD,
    0,
    0.78125
)

local adventurerLevelText = frameArtOverlay:CreateFontString(
    "AdventurerPlayerLevelText",
    "OVERLAY",
    "GameFontNormalSmall"
)
adventurerLevelText:SetPoint("CENTER", PlayerFrame, "CENTER", -63, -16)
adventurerLevelText:Hide()

local function UpdateBar(bar)
    local current = UnitPower("player", bar.powerId) or 0
    local maximum = UnitPowerMax("player", bar.powerId) or 0

    if maximum <= 0 then
        maximum = 1
    end

    bar:SetMinMaxValues(0, maximum)
    bar:SetValue(current)
    bar.valueText:SetText(labels[bar.powerId] .. " " .. current .. " / " .. maximum)
end

local function ApplyAdventurerPlayerFrameArt()
    if not PlayerFrame or not PlayerFrameTexture then
        return
    end

    PlayerFrameTexture:SetAlpha(0)
    if PlayerLevelText then
        PlayerLevelText:Hide()
    end

    frameArtOverlay:ClearAllPoints()
    frameArtOverlay:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", 0, 0)
    frameArtOverlay:SetWidth(ADVENTURER_FRAME_WIDTH)
    frameArtOverlay:SetHeight(ADVENTURER_FRAME_HEIGHT)
    frameArtOverlay:SetFrameStrata("HIGH")
    frameArtOverlay:SetFrameLevel(1)

    adventurerLevelText:SetText(UnitLevel("player") or "")
    adventurerLevelText:Show()
    frameArtOverlay:Show()
end

local function PositionNativeBarText()
    if PlayerFrameHealthBarText and PlayerFrameHealthBar then
        PlayerFrameHealthBarText:ClearAllPoints()
        PlayerFrameHealthBarText:SetPoint("CENTER", PlayerFrameHealthBar, "CENTER", 0, 0)
    end

    if PlayerFrameManaBarText and PlayerFrameManaBar then
        PlayerFrameManaBarText:ClearAllPoints()
        PlayerFrameManaBarText:SetPoint("CENTER", PlayerFrameManaBar, "CENTER", 0, 0)
    end
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

    PositionNativeBarText()
end

local function PositionAuxiliaryBars()
    if not PlayerFrame then
        return
    end

    rageBar:ClearAllPoints()
    rageBar:SetOrientation("HORIZONTAL")
    rageBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", RAGE_LEFT, -RAGE_TOP)
    rageBar:SetWidth(RAGE_WIDTH)
    rageBar:SetHeight(RAGE_HEIGHT)

    energyBar:ClearAllPoints()
    energyBar:SetOrientation("HORIZONTAL")
    energyBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", BAR_LEFT, -ENERGY_TOP)
    energyBar:SetWidth(BAR_WIDTH)
    energyBar:SetHeight(ENERGY_HEIGHT)
end

local function PositionBars()
    PositionNativeBars()
    PositionAuxiliaryBars()
    ApplyAdventurerPlayerFrameArt()
end

local function HideAdventurerResources()
    rageBar:Hide()
    energyBar:Hide()
    adventurerLevelText:Hide()
    frameArtOverlay:Hide()

    if PlayerFrameTexture then
        PlayerFrameTexture:SetAlpha(1)
    end
    if PlayerLevelText then
        PlayerLevelText:Show()
    end
end

local function PlayerIsUsingVehicleUI()
    return UnitHasVehicleUI and UnitHasVehicleUI("player")
end

-- ---------------------------------------------------------------------------
-- Combo points
-- ---------------------------------------------------------------------------
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

    rageBar:Show()
    energyBar:Show()

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
    elseif event == "PLAYER_TARGET_CHANGED" then
        SetVisibleComboPoints(0)
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
    PositionBars()

    if not rageBar:IsShown() then
        rageBar:Show()
        energyBar:Show()
    end
end)
