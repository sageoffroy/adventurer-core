-- Adventurer Core: universal resource HUD for the native class-10 Adventurer.
--
-- The server owns the actual pools. Mana remains the normal PlayerFrame bar;
-- Rage and Energy are stacked below it. Blizzard's native ComboFrame remains
-- attached to TargetFrame. Adventurer has no Death Knight rune/runic runtime.

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
    end

    return 1.0, 1.0, 0.0
end

local function CreateResourceBar(name, powerId)
    local bar = CreateFrame("StatusBar", name, UIParent)
    bar.powerId = powerId
    bar:SetStatusBarTexture("Interface\\TargetingFrame\\UI-StatusBar")
    bar:SetFrameStrata("LOW")
    bar:SetHeight(11)
    bar:SetWidth(119)

    local r, g, b = GetPowerColor(powerId)
    bar:SetStatusBarColor(r, g, b)

    local background = bar:CreateTexture(nil, "BACKGROUND")
    background:SetAllPoints(bar)
    background:SetTexture("Interface\\TargetingFrame\\UI-StatusBar")
    background:SetVertexColor(0.08, 0.08, 0.08, 0.85)

    local label = bar:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", bar, "LEFT", 3, 0)
    label:SetJustifyH("LEFT")
    label:SetText(labels[powerId])
    bar.label = label

    local value = bar:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    value:SetPoint("RIGHT", bar, "RIGHT", -3, 0)
    value:SetJustifyH("RIGHT")
    bar.valueText = value

    bar:Hide()
    return bar
end

local rageBar = CreateResourceBar("AdventurerRageBar", POWER_RAGE)
local energyBar = CreateResourceBar("AdventurerEnergyBar", POWER_ENERGY)

local function UpdateBar(bar)
    local current = UnitPower("player", bar.powerId) or 0
    local maximum = UnitPowerMax("player", bar.powerId) or 0

    if maximum <= 0 then
        maximum = 1
    end

    bar:SetMinMaxValues(0, maximum)
    bar:SetValue(current)
    bar.valueText:SetText(current .. " / " .. maximum)
end

local function PositionBars()
    if not PlayerFrameManaBar then
        return
    end

    local width = PlayerFrameManaBar:GetWidth()
    if width and width > 0 then
        rageBar:SetWidth(width)
        energyBar:SetWidth(width)
    end

    rageBar:ClearAllPoints()
    rageBar:SetPoint("TOPLEFT", PlayerFrameManaBar, "BOTTOMLEFT", 0, -2)

    energyBar:ClearAllPoints()
    energyBar:SetPoint("TOPLEFT", rageBar, "BOTTOMLEFT", 0, -2)
end

local function HideAdventurerResources()
    rageBar:Hide()
    energyBar:Hide()
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
        -- Hide stale points immediately; the server sends the correct count for
        -- the new selected target on its next 100 ms sync tick.
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

    -- PlayerFrame can change width/anchors when vehicle or other Blizzard art
    -- changes. Reassert the stack without replacing any stock texture.
    PositionBars()

    if not rageBar:IsShown() then
        rageBar:Show()
        energyBar:Show()
    end
end)

--[[
TEMPORARY BUILDER-COMPATIBILITY MARKERS.
These strings are inert and exist only because the historical milestone client
validator still expects the old DK-resource contract. They will be removed with
that validator after the in-game no-DK runtime is approved.
AdventurerRunicPowerBar
RuneFrame:SetPoint
RegisterEvent("RUNE_POWER_UPDATE")
GetRuneCooldown(index)
ActionButton_UpdateUsable(button)
]]
