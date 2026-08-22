-- Adventurer Core: universal resource HUD for the native class-10 Adventurer.
--
-- The server owns the actual pools. This file exposes them together in the
-- stock 3.3.5a UI: Mana remains the normal PlayerFrame bar; Rage, Energy and
-- Runic Power are stacked below it; the native Death Knight RuneFrame is reused
-- below the stack. Blizzard's native ComboFrame remains attached to TargetFrame.

local ADVENTURER_CLASS_ID = 10
local POWER_RAGE = 1
local POWER_ENERGY = 3
local POWER_RUNIC_POWER = 6
local COMBO_PREFIX = "AdventurerCP"
local MAX_RUNES = 6

local locale = GetLocale()
local labels
if locale == "esES" or locale == "esMX" then
    labels = {
        [POWER_RAGE] = "Ira",
        [POWER_ENERGY] = "Energía",
        [POWER_RUNIC_POWER] = "Poder rúnico",
    }
else
    labels = {
        [POWER_RAGE] = "Rage",
        [POWER_ENERGY] = "Energy",
        [POWER_RUNIC_POWER] = "Runic Power",
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
local runicBar = CreateResourceBar("AdventurerRunicPowerBar", POWER_RUNIC_POWER)

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
        runicBar:SetWidth(width)
    end

    rageBar:ClearAllPoints()
    rageBar:SetPoint("TOPLEFT", PlayerFrameManaBar, "BOTTOMLEFT", 0, -2)

    energyBar:ClearAllPoints()
    energyBar:SetPoint("TOPLEFT", rageBar, "BOTTOMLEFT", 0, -2)

    runicBar:ClearAllPoints()
    runicBar:SetPoint("TOPLEFT", energyBar, "BOTTOMLEFT", 0, -2)
end

local function RefreshRunes()
    if not RuneFrame then
        return
    end

    RuneFrame:ClearAllPoints()
    RuneFrame:SetScale(0.85)
    RuneFrame:SetPoint("TOPLEFT", runicBar, "BOTTOMLEFT", 2, -6)
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
-- when the action bar never receives ACTIONBAR_UPDATE_USABLE for class 10. Poll
-- the six native runes too; only when their ready mask changes do we ask the
-- stock action buttons to recalculate IsUsableAction.
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

    -- PlayerFrame can change width/anchors when vehicle or other Blizzard art
    -- changes. Reassert the stack without replacing any stock texture.
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
