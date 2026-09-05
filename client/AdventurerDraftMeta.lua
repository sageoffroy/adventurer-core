-- Adventurer SpellDraft meta-actions, bundle details and debug pool viewer.
-- Loaded after AdventurerResources.lua so the base three-card chooser remains the
-- authority for card selection. This layer adds meta-actions and developer UI.

local ADVENTURER_CLASS_ID = 10
local DRAFT_PREFIX = "AdventurerDraft"
local DRAFT_REROLL_MESSAGE = "ADRAFT_REROLL"
local DRAFT_BLESS_PREFIX = "ADRAFT_BLESS:"
local DRAFT_DESTROY_PREFIX = "ADRAFT_DESTROY:"
local DRAFT_DEBUG_POOL_MESSAGE = "ADRAFT_POOL"
local INITIAL_ACTIVE_SOURCE_LEVEL_CAP = 10
local DEBUG_VISIBLE_ROWS = 15

local locale = GetLocale()
local text
if locale == "esES" or locale == "esMX" then
    text = {
        reroll = "Relanzar",
        bless = "Bendecir",
        destroy = "Destruir",
        cancel = "Cancelar",
        blocked = "Bloqueada",
        rerolls = "Relanzamientos: %d",
        blessings = "Bendiciones: %d",
        destroys = "Destrucciones: %d",
        blessed = "Bendecida x%.1f",
        blessHint = "Selecciona una carta para bendecirla",
        destroyHint = "Selecciona una carta para destruirla",
        debug = "Pool debug",
        debugTitle = "SpellDraft - pools disponibles",
        activePool = "Habilidades disponibles (%d)",
        talentPool = "Talentos disponibles (%d)",
        debugHint = "Rueda del mouse para desplazarte. Tooltip al pasar por un icono.",
        choose = "Elegir",
        rank = "Rango %d/%d",
    }
else
    text = {
        reroll = "Reroll",
        bless = "Bless",
        destroy = "Destroy",
        cancel = "Cancel",
        blocked = "Blocked",
        rerolls = "Rerolls: %d",
        blessings = "Blessings: %d",
        destroys = "Destroys: %d",
        blessed = "Blessed x%.1f",
        blessHint = "Select a card to bless it",
        destroyHint = "Select a card to destroy it",
        debug = "Pool debug",
        debugTitle = "SpellDraft - available pools",
        activePool = "Available abilities (%d)",
        talentPool = "Available talents (%d)",
        debugHint = "Mouse wheel to scroll. Hover an icon for its tooltip.",
        choose = "Choose",
        rank = "Rank %d/%d",
    }
end

local isSpanish = locale == "esES" or locale == "esMX"
local rarityLabels = {
    common = isSpanish and "Común" or "Common",
    uncommon = isSpanish and "Poco común" or "Uncommon",
    rare = isSpanish and "Rara" or "Rare",
    epic = isSpanish and "Épica" or "Epic",
    legendary = isSpanish and "Legendaria" or "Legendary",
}

local rarityKeys = {
    [0] = "common",
    [1] = "uncommon",
    [2] = "rare",
    [3] = "epic",
    [4] = "legendary",
}

local rarityColors = {
    common = {1.00, 1.00, 1.00},
    uncommon = {0.12, 1.00, 0.00},
    rare = {0.00, 0.44, 0.87},
    epic = {0.64, 0.21, 0.93},
    legendary = {1.00, 0.50, 0.00},
}

-- Only EXTRA spells are listed here. The primary spell is already represented
-- by the large card icon and must never be repeated in this strip.
local extraSpellsByPrimary = {
    [2457] = {100},
    [71] = {355},
    [1784] = {921, 6770},
    [5487] = {6807, 6795, 99},
    [1515] = {883, 2641, 6991, 982},
}

-- The pool debug catalog is streamed by the server from authoritative cards.csv.
-- No card/talent relationships or rarities are hardcoded client-side.
local function IsAdventurer()
    local className, classToken, classId = UnitClass("player")
    if classId == ADVENTURER_CLASS_ID or classToken == "ADVENTURER" then
        return true
    end
    return className == "Adventurer" or className == "Aventurero" or className == "Aventurera"
end

local function SendDraftCommand(message)
    local target = UnitName("player")
    if target and target ~= "" then
        SendChatMessage(message, "WHISPER", nil, target)
    end
end

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

local function IsKnownSpell(spellId)
    if IsSpellKnown then
        return IsSpellKnown(spellId)
    end
    return false
end

local DraftFrame = AdventurerDraftFrame
if not DraftFrame then
    return
end

DraftFrame:SetHeight(350)
DraftFrame:SetBackdrop({
    bgFile = "Interface\\Buttons\\WHITE8X8",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
})
DraftFrame:SetBackdropColor(0.015, 0.015, 0.02, 1.0)
if DraftFrame.hint then
    DraftFrame.hint:ClearAllPoints()
    DraftFrame.hint:SetPoint("BOTTOM", DraftFrame, "BOTTOM", 0, 48)
end

local state = {
    rerolls = 0,
    blesses = 0,
    destroys = 0,
    blessedCardId = 0,
    blessMultiplierPercent = 0,
    mode = nil,
    offered = {},
    destroyed = {},
    destroyedAll = {},
    sessionRanks = {},
    pendingPickedCardId = nil,
    serverConfigKnown = false,
    serverRerollStart = 0,
    serverBlessStart = 0,
    serverDestroyStart = 0,
    serverSourceCap = 0,
    serverCatalogSize = 0,
    debugCatalog = {},
    debugCatalogLoading = false,
}

DraftFrame.metaStatus = DraftFrame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
DraftFrame.metaStatus:SetPoint("BOTTOM", DraftFrame, "BOTTOM", 0, 52)
DraftFrame.metaStatus:SetText("")

local function CreateActionButton(name, x)
    local button = CreateFrame("Button", name, DraftFrame, "UIPanelButtonTemplate")
    button:SetWidth(112)
    button:SetHeight(24)
    button:SetPoint("BOTTOM", DraftFrame, "BOTTOM", x, 18)
    return button
end

local rerollButton = CreateActionButton("AdventurerDraftRerollButton", -126)
local blessButton = CreateActionButton("AdventurerDraftBlessButton", 0)
local destroyButton = CreateActionButton("AdventurerDraftDestroyButton", 126)
rerollButton:SetText(text.reroll)
blessButton:SetText(text.bless)
destroyButton:SetText(text.destroy)

local debugButton = CreateFrame("Button", "AdventurerDraftPoolDebugButton", DraftFrame, "UIPanelButtonTemplate")
debugButton:SetWidth(90)
debugButton:SetHeight(20)
debugButton:SetPoint("TOPRIGHT", DraftFrame, "TOPRIGHT", -22, -19)
debugButton:SetText(text.debug)

local cardButtons = {}
for i = 1, 3 do
    local button = _G["AdventurerDraftCard" .. i]
    if button then
        button.adventurerOriginalDraftClick = button:GetScript("OnClick")
        button.adventurerMetaBadge = button:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        button.adventurerMetaBadge:SetPoint("TOPRIGHT", button, "TOPRIGHT", -8, -7)
        button.adventurerMetaBadge:SetText("")
        button.adventurerExtraIcons = {}
        button:SetBackdropColor(0.01, 0.01, 0.015, 1.0)

        -- Keep the card body black on hover. Feedback comes from a brighter
        -- border instead of the old blue-tinted background, which clashed with
        -- the black-backed spell icons.
        button:SetScript("OnEnter", function(self)
            if not self.spellId then
                return
            end
            local r, g, b, a = self:GetBackdropBorderColor()
            self.adventurerRestBorder = { r, g, b, a }
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:SetHyperlink("spell:" .. self.spellId)
            GameTooltip:Show()
            self:SetBackdropColor(0.01, 0.01, 0.015, 1.0)
            self:SetBackdropBorderColor(
                math.min(1, r + 0.25),
                math.min(1, g + 0.25),
                math.min(1, b + 0.25),
                1.0
            )
        end)
        button:SetScript("OnLeave", function(self)
            GameTooltip:Hide()
            self:SetBackdropColor(0.01, 0.01, 0.015, 1.0)
            local color = self.adventurerRestBorder
            if color then
                self:SetBackdropBorderColor(color[1], color[2], color[3], color[4] or 0.9)
            end
        end)

        for iconIndex = 1, 4 do
            local iconButton = CreateFrame("Button", nil, button)
            iconButton:SetWidth(24)
            iconButton:SetHeight(24)
            iconButton.texture = iconButton:CreateTexture(nil, "ARTWORK")
            iconButton.texture:SetAllPoints(iconButton)
            iconButton:Hide()
            iconButton:SetScript("OnEnter", function(self)
                if not self.spellId then return end
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:SetHyperlink("spell:" .. self.spellId)
                GameTooltip:Show()
            end)
            iconButton:SetScript("OnLeave", function()
                GameTooltip:Hide()
            end)
            table.insert(button.adventurerExtraIcons, iconButton)
        end
        table.insert(cardButtons, button)
    end
end

local function HideExtraIcons(button)
    if not button.adventurerExtraIcons then return end
    for _, iconButton in ipairs(button.adventurerExtraIcons) do
        iconButton.spellId = nil
        iconButton:Hide()
    end
end

local function RefreshExtraIcons(button, card)
    HideExtraIcons(button)
    if not card then return end

    if button.meta then
        if card.maxRank and card.maxRank > 1 then
            button.meta:SetText(string.format(text.rank, card.rank or 1, card.maxRank))
        else
            button.meta:SetText("")
        end
    end

    local extras = extraSpellsByPrimary[card.spellId]
    if extras and #extras > 0 then
        local spacing = 28
        local totalWidth = (#extras * 24) + ((#extras - 1) * 4)
        local firstX = math.floor((190 - totalWidth) / 2)
        for i, spellId in ipairs(extras) do
            local iconButton = button.adventurerExtraIcons[i]
            if iconButton then
                local _, _, icon = GetSpellInfo(spellId)
                iconButton.spellId = spellId
                iconButton.texture:SetTexture(icon or "Interface\\Icons\\INV_Misc_QuestionMark")
                iconButton:ClearAllPoints()
                iconButton:SetPoint("TOPLEFT", button, "TOPLEFT", firstX + ((i - 1) * spacing), -128)
                iconButton:Show()
            end
        end
        if button.choose then
            button.choose:ClearAllPoints()
            button.choose:SetPoint("TOP", button, "TOP", 0, -164)
        end
    elseif button.choose then
        button.choose:ClearAllPoints()
        if button.meta and card.maxRank and card.maxRank > 1 then
            button.choose:SetPoint("TOP", button.meta, "BOTTOM", 0, -10)
        else
            button.choose:SetPoint("TOP", button.rarity, "BOTTOM", 0, -10)
        end
    end
end

local debugFrame = CreateFrame("Frame", "AdventurerDraftPoolDebugFrame", UIParent)
debugFrame:SetWidth(760)
debugFrame:SetHeight(475)
debugFrame:SetPoint("CENTER", DraftFrame, "CENTER", 0, 0)
debugFrame:SetFrameStrata("FULLSCREEN_DIALOG")
debugFrame:SetFrameLevel(DraftFrame:GetFrameLevel() + 20)
debugFrame:SetBackdrop({
    bgFile = "Interface\\Buttons\\WHITE8X8",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
})
debugFrame:SetBackdropColor(0.015, 0.015, 0.02, 1.0)
debugFrame:EnableMouse(true)
debugFrame:SetMovable(true)
debugFrame:RegisterForDrag("LeftButton")
debugFrame:SetScript("OnDragStart", function(self) self:StartMoving() end)
debugFrame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
debugFrame:Hide()

debugFrame.title = debugFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
debugFrame.title:SetPoint("TOP", debugFrame, "TOP", 0, -20)
debugFrame.title:SetText(text.debugTitle)

debugFrame.runtime = debugFrame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
debugFrame.runtime:SetPoint("TOP", debugFrame, "TOP", 0, -43)
debugFrame.runtime:SetText("")

debugFrame.hint = debugFrame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
debugFrame.hint:SetPoint("BOTTOM", debugFrame, "BOTTOM", 0, 18)
debugFrame.hint:SetText(text.debugHint)

local closeDebug = CreateFrame("Button", nil, debugFrame, "UIPanelCloseButton")
closeDebug:SetPoint("TOPRIGHT", debugFrame, "TOPRIGHT", -8, -8)

local function CreatePoolColumn(x)
    local column = CreateFrame("Frame", nil, debugFrame)
    column:SetWidth(350)
    column:SetHeight(380)
    column:SetPoint("TOPLEFT", debugFrame, "TOPLEFT", x, -62)
    column.offset = 0
    column.items = {}
    column.rows = {}
    column.title = column:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    column.title:SetPoint("TOPLEFT", column, "TOPLEFT", 4, 0)

    for i = 1, DEBUG_VISIBLE_ROWS do
        local row = CreateFrame("Button", nil, column)
        row:SetWidth(340)
        row:SetHeight(22)
        row:SetPoint("TOPLEFT", column, "TOPLEFT", 4, -24 - ((i - 1) * 23))
        row.icon = row:CreateTexture(nil, "ARTWORK")
        row.icon:SetWidth(20)
        row.icon:SetHeight(20)
        row.icon:SetPoint("LEFT", row, "LEFT", 0, 0)
        row.name = row:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        row.name:SetPoint("LEFT", row.icon, "RIGHT", 6, 0)
        row.name:SetWidth(230)
        row.name:SetJustifyH("LEFT")
        row.meta = row:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
        row.meta:SetPoint("RIGHT", row, "RIGHT", -4, 0)
        row.meta:SetWidth(80)
        row.meta:SetJustifyH("RIGHT")
        row:SetScript("OnEnter", function(self)
            if not self.spellId then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:SetHyperlink("spell:" .. self.spellId)
            GameTooltip:Show()
        end)
        row:SetScript("OnLeave", function() GameTooltip:Hide() end)
        table.insert(column.rows, row)
    end

    column:EnableMouseWheel(true)
    column:SetScript("OnMouseWheel", function(self, delta)
        local maxOffset = math.max(0, #self.items - DEBUG_VISIBLE_ROWS)
        if delta < 0 then
            self.offset = math.min(maxOffset, self.offset + 1)
        else
            self.offset = math.max(0, self.offset - 1)
        end
        if self.refreshRows then self:refreshRows() end
    end)
    return column
end

local activeColumn = CreatePoolColumn(28)
local talentColumn = CreatePoolColumn(382)

local function BuildDebugList(kind)
    local items = {}
    for _, card in ipairs(state.debugCatalog) do
        if card.type == kind then
            local name = GetSpellInfo(card.spell) or ("Spell #" .. card.spell)
            card.debugName = name
            table.insert(items, card)
        end
    end
    table.sort(items, function(a, b)
        if a.level ~= b.level then return a.level < b.level end
        return (a.debugName or "") < (b.debugName or "")
    end)
    return items
end

local function ConfigureColumnRefresh(column)
    column.refreshRows = function(self)
        local maxOffset = math.max(0, #self.items - DEBUG_VISIBLE_ROWS)
        if self.offset > maxOffset then self.offset = maxOffset end
        for index, row in ipairs(self.rows) do
            local card = self.items[self.offset + index]
            if card then
                local _, _, icon = GetSpellInfo(card.spell)
                local color = rarityColors[card.rarity] or rarityColors.common
                row.spellId = card.spell
                row.icon:SetTexture(icon or "Interface\\Icons\\INV_Misc_QuestionMark")
                row.name:SetText(card.debugName or ("Spell #" .. card.spell))
                row.name:SetTextColor(color[1], color[2], color[3])
                local rank = card.currentRank or 0
                if card.maxRank and card.maxRank > 1 then
                    local nextRank = math.min(rank + 1, card.maxRank)
                    row.meta:SetText(string.format("Lv%d  %d/%d", card.level, nextRank, card.maxRank))
                else
                    row.meta:SetText("Lv" .. card.level)
                end
                row:Show()
            else
                row.spellId = nil
                row:Hide()
            end
        end
    end
end
ConfigureColumnRefresh(activeColumn)
ConfigureColumnRefresh(talentColumn)

local function RefreshDebugPool()
    if state.serverConfigKnown then
        debugFrame.runtime:SetText(string.format("Server config: R%d B%d D%d  cap %d  catalog %d", state.serverRerollStart, state.serverBlessStart, state.serverDestroyStart, state.serverSourceCap, state.serverCatalogSize))
    else
        debugFrame.runtime:SetText("Server config: old SpellDraft runtime / no report")
    end
    activeColumn.items = BuildDebugList("active")
    talentColumn.items = BuildDebugList("talent")
    activeColumn.title:SetText(string.format(text.activePool, #activeColumn.items))
    talentColumn.title:SetText(string.format(text.talentPool, #talentColumn.items))
    activeColumn:refreshRows()
    talentColumn:refreshRows()
end

local function RequestDebugPool()
    state.debugCatalog = {}
    state.debugCatalogLoading = true
    RefreshDebugPool()
    SendDraftCommand(DRAFT_DEBUG_POOL_MESSAGE)
end

local function ToggleDebugPool()
    if debugFrame:IsShown() then
        debugFrame:Hide()
    else
        debugFrame:ClearAllPoints()
        debugFrame:SetPoint("CENTER", DraftFrame, "CENTER", 0, 0)
        debugFrame:SetFrameLevel(DraftFrame:GetFrameLevel() + 20)
        debugFrame:Show()
        RequestDebugPool()
    end
end

debugButton:SetScript("OnClick", ToggleDebugPool)
SLASH_ADVENTURERDRAFTPOOL1 = "/adraftpool"
SlashCmdList["ADVENTURERDRAFTPOOL"] = ToggleDebugPool

local function ResetMode()
    state.mode = nil
    blessButton:SetText(text.bless)
    destroyButton:SetText(text.destroy)
    if DraftFrame.hint then
        DraftFrame.hint:SetText("")
    end
end

local function RefreshMetaUI()
    local blessMultiplier = (state.blessMultiplierPercent or 0) / 100
    local status = string.format(text.rerolls, state.rerolls)
        .. "   •   "
        .. string.format(text.blessings, state.blesses)
        .. "   •   "
        .. string.format(text.destroys, state.destroys)
    if state.blessedCardId and state.blessedCardId > 0 and blessMultiplier > 0 then
        status = status .. "   •   " .. string.format(text.blessed, blessMultiplier)
    end
    DraftFrame.metaStatus:SetText(status)

    if state.rerolls > 0 and DraftFrame:IsShown() then rerollButton:Enable() else rerollButton:Disable() end
    if state.blesses > 0 and state.blessMultiplierPercent > 0 and DraftFrame:IsShown() then blessButton:Enable() else blessButton:Disable() end
    if state.destroys > 0 and DraftFrame:IsShown() then destroyButton:Enable() else destroyButton:Disable() end

    for _, button in ipairs(cardButtons) do
        local cardId = button.cardId
        local isDestroyed = cardId and state.destroyed[cardId]
        button:SetBackdropColor(0.01, 0.01, 0.015, 1.0)
        if isDestroyed then
            button:Disable()
            button:SetAlpha(0.30)
            if button.choose then button.choose:SetText(text.blocked) end
            button.adventurerMetaBadge:SetText("X")
            button.adventurerMetaBadge:SetTextColor(0.55, 0.55, 0.55)
        else
            if cardId and DraftFrame:IsShown() then
                button:Enable()
                button:SetAlpha(1)
            end
            if button.choose then button.choose:SetText(text.choose) end
            if cardId and cardId == state.blessedCardId then
                button.adventurerMetaBadge:SetText("★")
                button.adventurerMetaBadge:SetTextColor(1, 0.82, 0)
            else
                button.adventurerMetaBadge:SetText("")
            end
        end
    end

    if debugFrame:IsShown() then RefreshDebugPool() end
end

for _, button in ipairs(cardButtons) do
    button:SetScript("OnClick", function(self, mouseButton)
        if not self.cardId or state.destroyed[self.cardId] then return end

        if state.mode == "bless" then
            SendDraftCommand(DRAFT_BLESS_PREFIX .. self.cardId)
            ResetMode()
            return
        end

        if state.mode == "destroy" then
            SendDraftCommand(DRAFT_DESTROY_PREFIX .. self.cardId)
            ResetMode()
            destroyButton:Disable()
            return
        end

        state.pendingPickedCardId = self.cardId
        if self.adventurerOriginalDraftClick then
            self.adventurerOriginalDraftClick(self, mouseButton)
        end
    end)
end

rerollButton:SetScript("OnClick", function()
    if state.rerolls <= 0 then return end
    ResetMode()
    rerollButton:Disable()
    SendDraftCommand(DRAFT_REROLL_MESSAGE)
end)

blessButton:SetScript("OnClick", function()
    if state.blesses <= 0 then return end
    if state.mode == "bless" then
        ResetMode()
    else
        state.mode = "bless"
        blessButton:SetText(text.cancel)
        destroyButton:SetText(text.destroy)
        if DraftFrame.hint then DraftFrame.hint:SetText(text.blessHint) end
    end
end)

destroyButton:SetScript("OnClick", function()
    if state.destroys <= 0 then return end
    if state.mode == "destroy" then
        ResetMode()
    else
        state.mode = "destroy"
        destroyButton:SetText(text.cancel)
        blessButton:SetText(text.bless)
        if DraftFrame.hint then DraftFrame.hint:SetText(text.destroyHint) end
    end
end)

local function ConfirmPendingPick()
    local cardId = state.pendingPickedCardId
    if not cardId then return end
    state.sessionRanks[cardId] = (state.sessionRanks[cardId] or 0) + 1
    state.pendingPickedCardId = nil
end

local function ParseOffer(message)
    local sections = SplitText(message, "|")
    if #sections < 5 or sections[1] ~= "O" then return end

    state.offered = {}
    state.destroyed = {}
    local records = SplitText(sections[5], ";")
    for index, record in ipairs(records) do
        local fields = SplitText(record, ":")
        local cardId = tonumber(fields[1])
        local spellId = tonumber(fields[2])
        if cardId then
            table.insert(state.offered, cardId)
            local destroyed = tonumber(fields[8]) == 1
            state.destroyed[cardId] = destroyed
            if destroyed then state.destroyedAll[cardId] = true end

            local button = cardButtons[index]
            if button then
                RefreshExtraIcons(button, {
                    cardId = cardId,
                    spellId = spellId,
                    rank = tonumber(fields[6]) or 1,
                    maxRank = tonumber(fields[7]) or 1,
                })
            end
        end
    end
    for index = #records + 1, #cardButtons do
        HideExtraIcons(cardButtons[index])
    end
end

local function ParseDebugPool(message)
    local fields = SplitText(message, "|")
    if #fields < 2 or fields[1] ~= "D" then return end

    if fields[2] == "B" then
        state.debugCatalog = {}
        state.debugCatalogLoading = true
        if tonumber(fields[3]) then
            state.serverCatalogSize = tonumber(fields[3])
        end
        return
    end

    if fields[2] == "C" and #fields >= 9 then
        local kind = fields[3] == "A" and "active" or (fields[3] == "T" and "talent" or nil)
        local cardId = tonumber(fields[4])
        local spellId = tonumber(fields[5])
        local rarity = rarityKeys[tonumber(fields[6]) or 0] or "common"
        local level = tonumber(fields[7]) or 1
        local currentRank = tonumber(fields[8]) or 0
        local maxRank = tonumber(fields[9]) or 1
        if kind and cardId and spellId then
            table.insert(state.debugCatalog, {
                id = cardId,
                type = kind,
                spell = spellId,
                rarity = rarity,
                level = level,
                currentRank = currentRank,
                maxRank = maxRank,
            })
        end
        return
    end

    if fields[2] == "E" then
        state.debugCatalogLoading = false
        if debugFrame:IsShown() then RefreshDebugPool() end
    end
end

local function ParseMeta(message)
    local fields = SplitText(message, "|")
    if #fields < 5 or fields[1] ~= "M" then return end
    state.rerolls = tonumber(fields[2]) or 0
    state.destroys = tonumber(fields[3]) or 0
    state.blessedCardId = tonumber(fields[4]) or 0
    state.blessMultiplierPercent = tonumber(fields[5]) or 0
    state.blesses = tonumber(fields[6]) or 0
    state.serverConfigKnown = #fields >= 11
    state.serverRerollStart = tonumber(fields[7]) or 0
    state.serverBlessStart = tonumber(fields[8]) or 0
    state.serverDestroyStart = tonumber(fields[9]) or 0
    state.serverSourceCap = tonumber(fields[10]) or 0
    state.serverCatalogSize = tonumber(fields[11]) or 0
    RefreshMetaUI()
end

local function MetaWhisperFilter(_, _, message, sender)
    if not IsAdventurer() or sender ~= UnitName("player") then return false end
    if message == DRAFT_DEBUG_POOL_MESSAGE then return true end
    if message == DRAFT_REROLL_MESSAGE then return true end
    if string.sub(message, 1, string.len(DRAFT_BLESS_PREFIX)) == DRAFT_BLESS_PREFIX then return true end
    if string.sub(message, 1, string.len(DRAFT_DESTROY_PREFIX)) == DRAFT_DESTROY_PREFIX then return true end
    return false
end

ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER", MetaWhisperFilter)
ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER_INFORM", MetaWhisperFilter)

local MetaEventFrame = CreateFrame("Frame", "AdventurerDraftMetaEventFrame", UIParent)
MetaEventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
MetaEventFrame:RegisterEvent("CHAT_MSG_ADDON")
MetaEventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "PLAYER_ENTERING_WORLD" then
        ResetMode()
        RefreshMetaUI()
        return
    end

    local prefix, message = ...
    if not IsAdventurer() or prefix ~= DRAFT_PREFIX or not message then return end

    if string.sub(message, 1, 2) == "O|" then
        ConfirmPendingPick()
        ParseOffer(message)
        ResetMode()
        RefreshMetaUI()
        if debugFrame:IsShown() then RequestDebugPool() end
    elseif string.sub(message, 1, 2) == "D|" then
        ParseDebugPool(message)
    elseif string.sub(message, 1, 2) == "M|" then
        ParseMeta(message)
    elseif message == "C" then
        ConfirmPendingPick()
        state.destroyed = {}
        for _, button in ipairs(cardButtons) do HideExtraIcons(button) end
        ResetMode()
        RefreshMetaUI()
        if debugFrame:IsShown() then RequestDebugPool() end
    elseif string.sub(message, 1, 2) == "E|" then
        state.pendingPickedCardId = nil
        ResetMode()
        RefreshMetaUI()
    end
end)

-- ---------------------------------------------------------------------------
-- SpellDraft v2 chooser UX: minimize, combat suppression and minimap access.
-- ---------------------------------------------------------------------------
local draftUxText
if isSpanish then
    draftUxText = {
        pending = "SpellDraft pendiente",
        open = "Clic para abrir las elecciones pendientes.",
        combat = "No se abre durante el combate.",
    }
else
    draftUxText = {
        pending = "SpellDraft pending",
        open = "Click to open pending choices.",
        combat = "Cannot open during combat.",
    }
end

local hasPendingOffer = false
local userMinimized = false

local function IsPlayerInCombat()
    return UnitAffectingCombat and UnitAffectingCombat("player")
end

-- Keep the close button visually attached to Pool debug instead of positioning
-- both controls independently against the outer frame.
debugButton:ClearAllPoints()
debugButton:SetPoint("TOPRIGHT", DraftFrame, "TOPRIGHT", -42, -19)

local closeDraft = CreateFrame("Button", "AdventurerDraftCloseButton", DraftFrame, "UIPanelCloseButton")
closeDraft:SetPoint("LEFT", debugButton, "RIGHT", 0, 0)

-- Use the native minimap-button proportions and border offsets. Anchoring the
-- button center on the minimap's left edge keeps it seated on the circular rim
-- instead of floating inside the map at a resolution-dependent offset.
local minimapButton = CreateFrame("Button", "AdventurerDraftMinimapButton", Minimap)
minimapButton:SetWidth(32)
minimapButton:SetHeight(32)
minimapButton:SetFrameStrata("MEDIUM")
minimapButton:SetPoint("CENTER", Minimap, "LEFT", -5, -25)
minimapButton:EnableMouse(true)

minimapButton.icon = minimapButton:CreateTexture(nil, "ARTWORK")
minimapButton.icon:SetWidth(20)
minimapButton.icon:SetHeight(20)
minimapButton.icon:SetPoint("CENTER", minimapButton, "CENTER", 0, 0)
minimapButton.icon:SetTexture("Interface\\Icons\\INV_Misc_Book_09")
minimapButton.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)

minimapButton.border = minimapButton:CreateTexture(nil, "OVERLAY")
minimapButton.border:SetWidth(53)
minimapButton.border:SetHeight(53)
minimapButton.border:SetPoint("TOPLEFT", minimapButton, "TOPLEFT", 0, 0)
minimapButton.border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")

minimapButton:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
minimapButton:Hide()

local function RefreshDraftMinimapButton()
    if IsAdventurer() and hasPendingOffer then
        minimapButton:Show()
    else
        minimapButton:Hide()
    end
end

local function MinimizeDraftChooser()
    if not hasPendingOffer then
        return
    end
    userMinimized = true
    DraftFrame:Hide()
    debugFrame:Hide()
    RefreshDraftMinimapButton()
    RefreshMetaUI()
end

local function OpenDraftChooser()
    if not hasPendingOffer then
        return
    end
    if IsPlayerInCombat() then
        return
    end
    userMinimized = false
    DraftFrame:Show()
    RefreshDraftMinimapButton()
    RefreshMetaUI()
end

closeDraft:SetScript("OnClick", MinimizeDraftChooser)

minimapButton:SetScript("OnClick", function()
    OpenDraftChooser()
end)
minimapButton:SetScript("OnEnter", function(self)
    GameTooltip:SetOwner(self, "ANCHOR_LEFT")
    GameTooltip:AddLine(draftUxText.pending, 1, 0.82, 0)
    if IsPlayerInCombat() then
        GameTooltip:AddLine(draftUxText.combat, 1, 0.35, 0.35, true)
    else
        GameTooltip:AddLine(draftUxText.open, 1, 1, 1, true)
    end
    GameTooltip:Show()
end)
minimapButton:SetScript("OnLeave", function()
    GameTooltip:Hide()
end)

-- This tracker is intentionally separate from the base chooser event handler.
-- The base handler remains authoritative for parsing/building offers; this layer
-- only decides whether the already-built frame should be visible right now.
local DraftUxEventFrame = CreateFrame("Frame", "AdventurerDraftUxEventFrame", UIParent)
DraftUxEventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
DraftUxEventFrame:RegisterEvent("CHAT_MSG_ADDON")
DraftUxEventFrame:RegisterEvent("PLAYER_REGEN_DISABLED")
DraftUxEventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "PLAYER_ENTERING_WORLD" then
        if not IsAdventurer() then
            hasPendingOffer = false
            userMinimized = false
            minimapButton:Hide()
            debugFrame:Hide()
        end
        return
    end

    if event == "PLAYER_REGEN_DISABLED" then
        if hasPendingOffer then
            userMinimized = true
            DraftFrame:Hide()
            debugFrame:Hide()
            RefreshDraftMinimapButton()
            RefreshMetaUI()
        end
        return
    end

    local prefix, message = ...
    if not IsAdventurer() or prefix ~= DRAFT_PREFIX or not message then
        return
    end

    if string.sub(message, 1, 2) == "O|" then
        hasPendingOffer = true
        RefreshDraftMinimapButton()
        if userMinimized or IsPlayerInCombat() then
            if IsPlayerInCombat() then
                userMinimized = true
            end
            DraftFrame:Hide()
            debugFrame:Hide()
            RefreshMetaUI()
        end
    elseif message == "C" then
        hasPendingOffer = false
        userMinimized = false
        minimapButton:Hide()
        debugFrame:Hide()
    end
end)
