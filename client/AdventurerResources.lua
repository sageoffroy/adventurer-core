-- Adventurer Core: universal resource HUD for the native class-10 Adventurer.
--
-- The server owns the actual pools. This file only exposes them together in
-- the stock 3.3.5a UI: Mana remains the normal PlayerFrame bar; Rage, Energy
-- and Runic Power are stacked below it; the native Death Knight RuneFrame is
-- reused below the stack. Combo points deliberately stay on Blizzard's native
-- ComboFrame, which is already anchored to TargetFrame.

local ADVENTURER_CLASS_ID = 10
local POWER_RAGE = 1
local POWER_ENERGY = 3
local POWER_RUNIC_POWER = 6

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
    local className, _, classId = UnitClass("player")
    if classId == ADVENTURER_CLASS_ID then
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
    bar:SetHeight(10)
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
    rageBar:SetPoint("TOPLEFT", PlayerFrameManaBar, "BOTTOMLEFT", 0, -1)

    energyBar:ClearAllPoints()
    energyBar:SetPoint("TOPLEFT", rageBar, "BOTTOMLEFT", 0, -1)

    runicBar:ClearAllPoints()
    runicBar:SetPoint("TOPLEFT", energyBar, "BOTTOMLEFT", 0, -1)
end

local function RefreshRunes()
    if not RuneFrame then
        return
    end

    RuneFrame:ClearAllPoints()
    RuneFrame:SetScale(0.85)
    RuneFrame:SetPoint("TOPLEFT", runicBar, "BOTTOMLEFT", 2, -4)
    RuneFrame:Show()

    if RuneButton_Update then
        for index = 1, 6 do
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

    -- Blizzard's ComboFrame is intentionally left native. The core sends the
    -- normal SMSG_UPDATE_COMBO_POINTS packet, and stock ComboFrame is already
    -- attached to TargetFrame, so a generated combo point belongs over the
    -- enemy rather than in this player-resource stack.
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

AdventurerResourceFrame:SetScript("OnEvent", function(self, event, unit)
    if unit and unit ~= "player" and event ~= "PLAYER_TARGET_CHANGED" then
        return
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
    -- changes. Reassert the simple stack without replacing any stock texture.
    PositionBars()

    if not rageBar:IsShown() then
        rageBar:Show()
        energyBar:Show()
        runicBar:Show()
    end
    if RuneFrame and not RuneFrame:IsShown() then
        RefreshRunes()
    end
end)
