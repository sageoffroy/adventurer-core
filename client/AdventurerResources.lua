-- Adventurer Core: native PlayerFrame resource layout for class 10.
--
-- The frame art, Health and Mana stay on Blizzard's real PlayerFrame. Rage and
-- Energy are TextStatusBar children declared in AdventurerPlayerFrame.xml using
-- the same dimensions/anchors as the supplied classless reference layout.

local ADVENTURER_CLASS_ID = 10
local POWER_RAGE = 1
local POWER_ENERGY = 3
local COMBO_PREFIX = "AdventurerCP"

local ADVENTURER_FRAME_TEXTURE = "Interface\\Adventurer\\UI-AdventurerFrame"
local ADVENTURER_FRAME_TEX_LEFT = 1.0
local ADVENTURER_FRAME_TEX_RIGHT = 0.07421875
local ADVENTURER_FRAME_TEX_TOP = 0
local ADVENTURER_FRAME_TEX_BOTTOM = 0.78125

-- Internal PlayerFrame measurements copied from the reference PlayerFrame.xml.
local PLAYER_FRAME_WIDTH = 232
local PLAYER_FRAME_HEIGHT = 100
local PORTRAIT_LEFT = 42
local PORTRAIT_TOP = 12
local PORTRAIT_SIZE = 64

-- Final horizontal alignment: only the custom Adventurer BLP is offset.
-- Every native PlayerFrame child stays at its reference coordinate.
local FRAME_ART_X_SHIFT = 8
local RESOURCE_X_SHIFT = 0
local PORTRAIT_X_SHIFT = 0
local LEVEL_X_SHIFT = 0
local MANA_X_SHIFT = 0
local ENERGY_X_SHIFT = 0
local BACKGROUND_X_SHIFT = 0
local NAME_X_SHIFT = 0
local FLASH_X_SHIFT = 0
local STATUS_X_SHIFT = 0

local BACKGROUND_LEFT = 106
local BACKGROUND_TOP = 22
local BACKGROUND_WIDTH = 116
local BACKGROUND_HEIGHT = 41
local HEALTH_LEFT = 106
local HEALTH_TOP = 41
local HEALTH_WIDTH = 116
local HEALTH_HEIGHT = 12
local MANA_LEFT = 106
local MANA_TOP = 52
local MANA_WIDTH = 116
local MANA_HEIGHT = 12
local ENERGY_LEFT = 117
local ENERGY_TOP = 65
local ENERGY_WIDTH = 92
local ENERGY_HEIGHT = 11
local RAGE_RIGHT = 3
local RAGE_TOP = 24
local RAGE_WIDTH = 12
local RAGE_HEIGHT = 38
local FLASH_LEFT = 13
local FLASH_TOP = 0
local FLASH_WIDTH = 238
local FLASH_HEIGHT = 93
local STATUS_LEFT = 35
local STATUS_TOP = 8
local STATUS_WIDTH = 187
local STATUS_HEIGHT = 66

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

    return className == "Adventurer"
        or className == "Aventurero"
        or className == "Aventurera"
end

local function PlayerIsUsingVehicleUI()
    return UnitHasVehicleUI and UnitHasVehicleUI("player")
end

local function SetFramePoint(frame, point, relativeTo, relativePoint, x, y)
    if not frame then
        return
    end
    frame:ClearAllPoints()
    frame:SetPoint(point, relativeTo, relativePoint, x, y)
end

local function PositionNativeText()
    if PlayerFrameHealthBarText then
        SetFramePoint(PlayerFrameHealthBarText, "CENTER", PlayerFrame, "CENTER", 50 + RESOURCE_X_SHIFT, 3)
    end
    if PlayerFrameManaBarText then
        SetFramePoint(PlayerFrameManaBarText, "CENTER", PlayerFrame, "CENTER", 50 + MANA_X_SHIFT, -8)
    end
    if PlayerFrameEnergyBarText then
        SetFramePoint(PlayerFrameEnergyBarText, "CENTER", PlayerFrame, "CENTER", 50 + ENERGY_X_SHIFT, -22)
    end
    if PlayerFrameRageBarText then
        SetFramePoint(PlayerFrameRageBarText, "CENTER", PlayerFrame, "TOPRIGHT", -2 + RESOURCE_X_SHIFT, -42)
    end
end

local function ApplyReferencePlayerFrameLayout()
    if not PlayerFrame or not PlayerFrameHealthBar or not PlayerFrameManaBar then
        return
    end

    PlayerFrame:SetWidth(PLAYER_FRAME_WIDTH)
    PlayerFrame:SetHeight(PLAYER_FRAME_HEIGHT)

    if PlayerPortrait then
        PlayerPortrait:SetWidth(PORTRAIT_SIZE)
        PlayerPortrait:SetHeight(PORTRAIT_SIZE)
        SetFramePoint(PlayerPortrait, "TOPLEFT", PlayerFrame, "TOPLEFT", PORTRAIT_LEFT + PORTRAIT_X_SHIFT, -PORTRAIT_TOP)
    end

    if PlayerFrameBackground then
        PlayerFrameBackground:SetWidth(BACKGROUND_WIDTH)
        PlayerFrameBackground:SetHeight(BACKGROUND_HEIGHT)
        SetFramePoint(PlayerFrameBackground, "TOPLEFT", PlayerFrame, "TOPLEFT", BACKGROUND_LEFT + BACKGROUND_X_SHIFT, -BACKGROUND_TOP)
    end

    if PlayerFrameTexture then
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

    if PlayerFrameFlash then
        PlayerFrameFlash:SetWidth(FLASH_WIDTH)
        PlayerFrameFlash:SetHeight(FLASH_HEIGHT)
        SetFramePoint(PlayerFrameFlash, "TOPLEFT", PlayerFrame, "TOPLEFT", FLASH_LEFT + FLASH_X_SHIFT, -FLASH_TOP)
    end

    if PlayerStatusTexture then
        PlayerStatusTexture:SetWidth(STATUS_WIDTH)
        PlayerStatusTexture:SetHeight(STATUS_HEIGHT)
        SetFramePoint(PlayerStatusTexture, "TOPLEFT", PlayerFrame, "TOPLEFT", STATUS_LEFT + STATUS_X_SHIFT, -STATUS_TOP)
    end

    if PlayerName then
        SetFramePoint(PlayerName, "CENTER", PlayerFrame, "CENTER", 50 + NAME_X_SHIFT, 19)
    end
    if PlayerLevelText then
        SetFramePoint(PlayerLevelText, "CENTER", PlayerFrame, "CENTER", -63 + LEVEL_X_SHIFT, -16)
        PlayerLevelText:Show()
    end

    PlayerFrameHealthBar:SetWidth(HEALTH_WIDTH)
    PlayerFrameHealthBar:SetHeight(HEALTH_HEIGHT)
    SetFramePoint(PlayerFrameHealthBar, "TOPLEFT", PlayerFrame, "TOPLEFT", HEALTH_LEFT + RESOURCE_X_SHIFT, -HEALTH_TOP)

    PlayerFrameManaBar:SetWidth(MANA_WIDTH)
    PlayerFrameManaBar:SetHeight(MANA_HEIGHT)
    SetFramePoint(PlayerFrameManaBar, "TOPLEFT", PlayerFrame, "TOPLEFT", MANA_LEFT + MANA_X_SHIFT, -MANA_TOP)

    if PlayerFrameEnergyBar then
        PlayerFrameEnergyBar:SetWidth(ENERGY_WIDTH)
        PlayerFrameEnergyBar:SetHeight(ENERGY_HEIGHT)
        SetFramePoint(PlayerFrameEnergyBar, "TOPLEFT", PlayerFrame, "TOPLEFT", ENERGY_LEFT + ENERGY_X_SHIFT, -ENERGY_TOP)
    end

    if PlayerFrameRageBar then
        PlayerFrameRageBar:SetOrientation("VERTICAL")
        PlayerFrameRageBar:SetWidth(RAGE_WIDTH)
        PlayerFrameRageBar:SetHeight(RAGE_HEIGHT)
        SetFramePoint(PlayerFrameRageBar, "TOPRIGHT", PlayerFrame, "TOPRIGHT", RAGE_RIGHT + RESOURCE_X_SHIFT, -RAGE_TOP)
    end

    PositionNativeText()
end

local function UpdateAuxiliaryBar(bar, powerId, valueText)
    if not bar then
        return
    end

    local current = UnitPower("player", powerId) or 0
    local maximum = UnitPowerMax("player", powerId) or 0
    if maximum <= 0 then
        maximum = 1
    end

    bar:SetMinMaxValues(0, maximum)
    bar:SetValue(current)

    if valueText then
        valueText:SetText(labels[powerId] .. " " .. current .. " / " .. maximum)
    end
end

local function ConfigureAuxiliaryMouse(bar, valueText)
    if not bar or bar.adventurerMouseConfigured then
        return
    end

    bar.adventurerMouseConfigured = true
    bar:EnableMouse(true)
    bar:SetScript("OnEnter", function()
        if valueText then
            valueText:Show()
        end
    end)
    bar:SetScript("OnLeave", function()
        if valueText then
            valueText:Hide()
        end
    end)
end

local function HideAdventurerResources()
    if PlayerFrameEnergyBar then
        PlayerFrameEnergyBar:Hide()
    end
    if PlayerFrameRageBar then
        PlayerFrameRageBar:Hide()
    end
    if PlayerFrameEnergyBarText then
        PlayerFrameEnergyBarText:Hide()
    end
    if PlayerFrameRageBarText then
        PlayerFrameRageBarText:Hide()
    end
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
        HideAdventurerResources()
        return
    end

    if PlayerIsUsingVehicleUI() then
        HideAdventurerResources()
        return
    end

    ApplyReferencePlayerFrameLayout()

    ConfigureAuxiliaryMouse(PlayerFrameEnergyBar, PlayerFrameEnergyBarText)
    ConfigureAuxiliaryMouse(PlayerFrameRageBar, PlayerFrameRageBarText)

    UpdateAuxiliaryBar(PlayerFrameEnergyBar, POWER_ENERGY, PlayerFrameEnergyBarText)
    UpdateAuxiliaryBar(PlayerFrameRageBar, POWER_RAGE, PlayerFrameRageBarText)

    if PlayerFrameEnergyBar then
        PlayerFrameEnergyBar:Show()
    end
    if PlayerFrameRageBar then
        PlayerFrameRageBar:Show()
    end

    if ComboFrame_Update then
        ComboFrame_Update()
    end
end

-- Blizzard's PlayerFrame_ToPlayerArt reapplies the stock 119px bar widths after
-- vehicle transitions and PLAYER_ENTERING_WORLD. Reapply the Adventurer layout
-- immediately after the native function instead of fighting it with a separate
-- art overlay.
if hooksecurefunc and PlayerFrame_ToPlayerArt then
    hooksecurefunc("PlayerFrame_ToPlayerArt", function()
        if IsAdventurer() and not PlayerIsUsingVehicleUI() then
            ApplyReferencePlayerFrameLayout()
        end
    end)
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

    UpdateAuxiliaryBar(PlayerFrameEnergyBar, POWER_ENERGY, PlayerFrameEnergyBarText)
    UpdateAuxiliaryBar(PlayerFrameRageBar, POWER_RAGE, PlayerFrameRageBarText)

    -- Keep exact geometry stable if another stock PlayerFrame transition ran.
    ApplyReferencePlayerFrameLayout()

    if PlayerFrameEnergyBar and not PlayerFrameEnergyBar:IsShown() then
        PlayerFrameEnergyBar:Show()
    end
    if PlayerFrameRageBar and not PlayerFrameRageBar:IsShown() then
        PlayerFrameRageBar:Show()
    end
end)

-- ---------------------------------------------------------------------------
-- Talent window cleanup
-- ---------------------------------------------------------------------------
-- Some 3.3.5a interface stacks add a permanent helper label to the talent
-- window telling the player to "mouseover" / "mouse over" a talent. Adventurer
-- has no use for that instruction. Remove only matching FontStrings that belong
-- to PlayerTalentFrame; do not alter global localized strings or other tooltips.
local function IsMouseoverInstruction(text)
    if type(text) ~= "string" then
        return false
    end

    local lowered = string.lower(text)
    return string.find(lowered, "mouseover", 1, true) ~= nil
        or string.find(lowered, "mouse over", 1, true) ~= nil
end

local function HideMouseoverInstructionInFrame(frame)
    if not frame then
        return
    end

    local regions = { frame:GetRegions() }
    for _, region in ipairs(regions) do
        if region and region.GetText then
            local text = region:GetText()
            if IsMouseoverInstruction(text) then
                region:SetText("")
                region:Hide()
            end
        end
    end

    local children = { frame:GetChildren() }
    for _, child in ipairs(children) do
        HideMouseoverInstructionInFrame(child)
    end
end

local talentCleanupInstalled = false
local function CleanupAdventurerTalentWindow()
    if IsAdventurer() and PlayerTalentFrame then
        HideMouseoverInstructionInFrame(PlayerTalentFrame)
    end
end

local function InstallAdventurerTalentWindowCleanup()
    if talentCleanupInstalled or not PlayerTalentFrame then
        return
    end

    talentCleanupInstalled = true
    PlayerTalentFrame:HookScript("OnShow", CleanupAdventurerTalentWindow)

    if hooksecurefunc and PlayerTalentFrame_Refresh then
        hooksecurefunc("PlayerTalentFrame_Refresh", CleanupAdventurerTalentWindow)
    end

    CleanupAdventurerTalentWindow()
end

local AdventurerTalentUICleanupFrame = CreateFrame("Frame")
AdventurerTalentUICleanupFrame:RegisterEvent("ADDON_LOADED")
AdventurerTalentUICleanupFrame:SetScript("OnEvent", function(self, event, addonName)
    if addonName == "Blizzard_TalentUI" then
        InstallAdventurerTalentWindowCleanup()
        self:UnregisterEvent("ADDON_LOADED")
    end
end)

-- Covers clients where Blizzard_TalentUI is already loaded before this file.
InstallAdventurerTalentWindowCleanup()
