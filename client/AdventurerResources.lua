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
-- Adventurer Draft v1: minimal three-card chooser
-- ---------------------------------------------------------------------------
local DRAFT_PREFIX = "AdventurerDraft"
local DRAFT_READY_MESSAGE = "ADRAFT_READY"
local DRAFT_PICK_PREFIX = "ADRAFT_PICK:"
local DRAFT_BUTTON_COUNT = 3

local draftText
if locale == "esES" or locale == "esMX" then
    draftText = {
        activeTitle = "Elige una habilidad",
        talentTitle = "Elige un talento",
        activePending = "Habilidades pendientes: %d",
        talentPending = "Talentos pendientes: %d",
        rank = "Rango %d/%d",
        bundle = "Incluye %d habilidades",
        choose = "Elegir",
        waiting = "Aprendiendo...",
        error = "El servidor rechazó la elección (%s).",
        rarity = { "Común", "Poco común", "Rara", "Épica", "Legendaria" },
    }
else
    draftText = {
        activeTitle = "Choose an ability",
        talentTitle = "Choose a talent",
        activePending = "Pending abilities: %d",
        talentPending = "Pending talents: %d",
        rank = "Rank %d/%d",
        bundle = "Includes %d abilities",
        choose = "Choose",
        waiting = "Learning...",
        error = "The server rejected the choice (%s).",
        rarity = { "Common", "Uncommon", "Rare", "Epic", "Legendary" },
    }
end

local rarityColors = {
    { 1.00, 1.00, 1.00 },
    { 0.12, 1.00, 0.00 },
    { 0.00, 0.44, 0.87 },
    { 0.64, 0.21, 0.93 },
    { 1.00, 0.50, 0.00 },
}

local function SplitText(value, separator)
    local parts = {}
    if not value or value == "" then
        return parts
    end

    local start = 1
    while true do
        local first, last = string.find(value, separator, start, true)
        if not first then
            table.insert(parts, string.sub(value, start))
            break
        end
        table.insert(parts, string.sub(value, start, first - 1))
        start = last + 1
    end
    return parts
end

local DraftFrame = CreateFrame("Frame", "AdventurerDraftFrame", UIParent)
DraftFrame:SetWidth(650)
DraftFrame:SetHeight(300)
DraftFrame:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
DraftFrame:SetFrameStrata("FULLSCREEN_DIALOG")
DraftFrame:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
})
DraftFrame:SetBackdropColor(0.05, 0.05, 0.08, 0.98)
DraftFrame:EnableMouse(true)
DraftFrame:SetMovable(true)
DraftFrame:RegisterForDrag("LeftButton")
DraftFrame:SetScript("OnDragStart", function(self) self:StartMoving() end)
DraftFrame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
DraftFrame:Hide()

DraftFrame.title = DraftFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
DraftFrame.title:SetPoint("TOP", DraftFrame, "TOP", 0, -22)
DraftFrame.title:SetText("Adventurer Draft")

DraftFrame.status = DraftFrame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
DraftFrame.status:SetPoint("TOP", DraftFrame.title, "BOTTOM", 0, -6)
DraftFrame.status:SetText("")

DraftFrame.hint = DraftFrame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
DraftFrame.hint:SetPoint("BOTTOM", DraftFrame, "BOTTOM", 0, 14)
DraftFrame.hint:SetText("Mouseover: detalles de la habilidad")
if locale ~= "esES" and locale ~= "esMX" then
    DraftFrame.hint:SetText("Mouseover: ability details")
end

local draftButtons = {}

local function SetDraftButtonsEnabled(enabled)
    for _, button in ipairs(draftButtons) do
        if enabled then
            button:Enable()
            button:SetAlpha(1)
            button.choose:SetText(draftText.choose)
        else
            button:Disable()
            button:SetAlpha(0.55)
            button.choose:SetText(draftText.waiting)
        end
    end
end

local function SendDraftCommand(message)
    local target = UnitName("player")
    if target and target ~= "" then
        SendChatMessage(message, "WHISPER", nil, target)
    end
end

for index = 1, DRAFT_BUTTON_COUNT do
    local button = CreateFrame("Button", "AdventurerDraftCard" .. index, DraftFrame)
    button:SetWidth(190)
    button:SetHeight(205)
    button:SetPoint("TOPLEFT", DraftFrame, "TOPLEFT", 28 + (index - 1) * 202, -68)
    button:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8X8",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true,
        tileSize = 16,
        edgeSize = 14,
        insets = { left = 3, right = 3, top = 3, bottom = 3 },
    })
    button:SetBackdropColor(0.03, 0.04, 0.07, 0.96)
    button:SetBackdropBorderColor(0.55, 0.55, 0.60, 1)

    button.icon = button:CreateTexture(nil, "ARTWORK")
    button.icon:SetWidth(56)
    button.icon:SetHeight(56)
    button.icon:SetPoint("TOP", button, "TOP", 0, -15)
    button.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")

    button.name = button:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    button.name:SetWidth(170)
    button.name:SetPoint("TOP", button.icon, "BOTTOM", 0, -8)
    button.name:SetJustifyH("CENTER")
    button.name:SetText("-")

    button.rarity = button:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    button.rarity:SetPoint("TOP", button.name, "BOTTOM", 0, -5)
    button.rarity:SetText("")

    button.meta = button:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    button.meta:SetWidth(170)
    button.meta:SetPoint("TOP", button.rarity, "BOTTOM", 0, -4)
    button.meta:SetJustifyH("CENTER")
    button.meta:SetText("")

    button.choose = button:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    button.choose:SetPoint("BOTTOM", button, "BOTTOM", 0, 12)
    button.choose:SetText(draftText.choose)

    button:SetScript("OnEnter", function(self)
        if not self.spellId then
            return
        end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("spell:" .. self.spellId)
        GameTooltip:Show()
        if self:IsEnabled() then
            self:SetBackdropColor(0.10, 0.12, 0.18, 0.98)
        end
    end)
    button:SetScript("OnLeave", function(self)
        GameTooltip:Hide()
        self:SetBackdropColor(0.03, 0.04, 0.07, 0.96)
    end)
    button:SetScript("OnClick", function(self)
        if not self.cardId then
            return
        end
        SetDraftButtonsEnabled(false)
        SendDraftCommand(DRAFT_PICK_PREFIX .. self.cardId)
    end)

    table.insert(draftButtons, button)
end

local function HideDraftFrame()
    DraftFrame:Hide()
    for _, button in ipairs(draftButtons) do
        button.cardId = nil
        button.spellId = nil
        button:Hide()
    end
end

local function ParseDraftCard(record)
    local fields = SplitText(record, ":")
    if #fields < 7 then
        return nil
    end

    local card = {
        cardId = tonumber(fields[1]),
        spellId = tonumber(fields[2]),
        rarity = tonumber(fields[3]) or 0,
        weight = tonumber(fields[4]) or 100,
        grantCount = tonumber(fields[5]) or 1,
        rank = tonumber(fields[6]) or 1,
        maxRank = tonumber(fields[7]) or 1,
    }
    if not card.cardId or not card.spellId then
        return nil
    end
    return card
end

local function ShowDraftOffer(payload)
    local sections = SplitText(payload, "|")
    if #sections < 5 or sections[1] ~= "O" then
        return
    end

    local draftKind = sections[2]
    local pendingActive = tonumber(sections[3]) or 0
    local pendingTalent = tonumber(sections[4]) or 0
    local records = SplitText(sections[5], ";")

    if draftKind == "T" then
        DraftFrame.title:SetText(draftText.talentTitle)
    else
        DraftFrame.title:SetText(draftText.activeTitle)
    end
    DraftFrame.status:SetText(
        string.format(draftText.activePending, pendingActive)
        .. "   •   "
        .. string.format(draftText.talentPending, pendingTalent)
    )

    for index = 1, DRAFT_BUTTON_COUNT do
        local button = draftButtons[index]
        local card = records[index] and ParseDraftCard(records[index]) or nil
        if card then
            button.cardId = card.cardId
            button.spellId = card.spellId
            button.weight = card.weight

            local name, subName, icon = GetSpellInfo(card.spellId)
            button.name:SetText(name or ("Spell #" .. card.spellId))
            button.icon:SetTexture(icon or "Interface\\Icons\\INV_Misc_QuestionMark")

            local rarityIndex = math.max(0, math.min(4, card.rarity)) + 1
            local rarityName = draftText.rarity[rarityIndex] or ""
            local color = rarityColors[rarityIndex] or rarityColors[1]
            button.rarity:SetText(rarityName)
            button.rarity:SetTextColor(color[1], color[2], color[3])
            button:SetBackdropBorderColor(color[1], color[2], color[3], 0.9)

            local meta = {}
            if card.maxRank > 1 then
                table.insert(meta, string.format(draftText.rank, card.rank, card.maxRank))
            end
            if card.grantCount > 1 then
                table.insert(meta, string.format(draftText.bundle, card.grantCount))
            end
            button.meta:SetText(table.concat(meta, "\n"))
            button.choose:SetText(draftText.choose)
            button:Enable()
            button:SetAlpha(1)
            button:Show()
        else
            button.cardId = nil
            button.spellId = nil
            button:Hide()
        end
    end

    DraftFrame:Show()
end

local function HandleDraftServerMessage(message)
    if not message or message == "" then
        return
    end

    if string.sub(message, 1, 2) == "O|" then
        ShowDraftOffer(message)
    elseif message == "C" then
        HideDraftFrame()
    elseif string.sub(message, 1, 2) == "E|" then
        SetDraftButtonsEnabled(true)
        local errorCode = string.sub(message, 3)
        DEFAULT_CHAT_FRAME:AddMessage("|cffff5555[Adventurer Draft]|r " .. string.format(draftText.error, errorCode))
    end
end

local function DraftWhisperFilter(_, _, message, sender)
    if not IsAdventurer() or sender ~= UnitName("player") then
        return false
    end
    if message == DRAFT_READY_MESSAGE or string.sub(message, 1, string.len(DRAFT_PICK_PREFIX)) == DRAFT_PICK_PREFIX then
        return true
    end
    return false
end

ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER", DraftWhisperFilter)
ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER_INFORM", DraftWhisperFilter)

local AdventurerDraftEventFrame = CreateFrame("Frame", "AdventurerDraftEventFrame", UIParent)
AdventurerDraftEventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
AdventurerDraftEventFrame:RegisterEvent("CHAT_MSG_ADDON")
AdventurerDraftEventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "PLAYER_ENTERING_WORLD" then
        if not IsAdventurer() then
            HideDraftFrame()
            return
        end
        if RegisterAddonMessagePrefix then
            RegisterAddonMessagePrefix(DRAFT_PREFIX)
        end
        -- Ask the server to resend any persisted offer. A short delay is not
        -- required: if the server-side login hook already sent the offer this
        -- command is idempotent; otherwise it establishes the first one.
        SendDraftCommand(DRAFT_READY_MESSAGE)
        return
    end

    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if IsAdventurer() and prefix == DRAFT_PREFIX then
            HandleDraftServerMessage(message)
        end
    end
end)
