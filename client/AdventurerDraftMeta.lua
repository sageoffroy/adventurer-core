-- Adventurer SpellDraft meta-actions, bundle details and debug pool viewer.
-- Loaded after AdventurerResources.lua so the base three-card chooser remains the
-- authority for card selection. This layer adds meta-actions and developer UI.

local ADVENTURER_CLASS_ID = 10
local DRAFT_PREFIX = "AdventurerDraft"
local DRAFT_REROLL_MESSAGE = "ADRAFT_REROLL"
local DRAFT_BLESS_PREFIX = "ADRAFT_BLESS:"
local DRAFT_DESTROY_PREFIX = "ADRAFT_DESTROY:"
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

-- Client-side mirror used only by the debug window. Server cards.csv remains
-- authoritative for actual draws. Requirements use card IDs, matching cards.csv.
local debugCatalog = {
    { id=1, type="active", level=1, rarity="common", spell=2457, maxRank=1 },
    { id=2, type="active", level=1, rarity="common", spell=133, maxRank=1 },
    { id=3, type="active", level=4, rarity="common", spell=116, maxRank=1 },
    { id=4, type="active", level=1, rarity="common", spell=686, maxRank=1 },
    { id=5, type="active", level=1, rarity="common", spell=585, maxRank=1 },
    { id=6, type="active", level=1, rarity="common", spell=403, maxRank=1 },
    { id=7, type="active", level=1, rarity="common", spell=5176, maxRank=1 },
    { id=8, type="active", level=1, rarity="common", spell=78, maxRank=1 },
    { id=9, type="active", level=4, rarity="common", spell=774, maxRank=1 },
    { id=10, type="active", level=1, rarity="uncommon", spell=1784, maxRank=1 },
    { id=12, type="active", level=1, rarity="common", spell=1459, maxRank=1 },
    { id=13, type="active", level=1, rarity="common", spell=331, maxRank=1 },
    { id=14, type="active", level=1, rarity="common", spell=1752, maxRank=1 },
    { id=15, type="active", level=10, rarity="common", spell=71, maxRank=1 },
    { id=16, type="active", level=1, rarity="common", spell=5185, maxRank=1 },
    { id=17, type="active", level=1, rarity="uncommon", spell=1126, maxRank=1 },
    { id=18, type="active", level=4, rarity="uncommon", spell=8921, maxRank=1 },
    { id=19, type="active", level=6, rarity="common", spell=467, maxRank=1 },
    { id=20, type="active", level=8, rarity="uncommon", spell=339, maxRank=1 },
    { id=21, type="active", level=10, rarity="rare", spell=5487, maxRank=1 },
    { id=22, type="active", level=10, rarity="common", spell=18960, maxRank=1 },
    { id=23, type="active", level=1, rarity="common", spell=6673, maxRank=1 },
    { id=24, type="active", level=4, rarity="common", spell=772, maxRank=1, any={{1,1},{15,1}} },
    { id=25, type="active", level=6, rarity="common", spell=6343, maxRank=1, any={{1,1},{15,1}} },
    { id=26, type="active", level=6, rarity="common", spell=34428, maxRank=1, all={{1,1}} },
    { id=27, type="active", level=8, rarity="common", spell=1715, maxRank=1, all={{1,1}} },
    { id=28, type="active", level=10, rarity="common", spell=2687, maxRank=1 },
    { id=29, type="active", level=10, rarity="common", spell=7386, maxRank=1 },
    { id=30, type="active", level=1, rarity="common", spell=635, maxRank=1 },
    { id=31, type="active", level=1, rarity="common", spell=21084, maxRank=1 },
    { id=32, type="active", level=1, rarity="common", spell=465, maxRank=1 },
    { id=33, type="active", level=4, rarity="common", spell=19740, maxRank=1 },
    { id=34, type="active", level=4, rarity="common", spell=20271, maxRank=1, all={{31,1}} },
    { id=35, type="active", level=6, rarity="common", spell=498, maxRank=1 },
    { id=36, type="active", level=8, rarity="common", spell=853, maxRank=1 },
    { id=37, type="active", level=8, rarity="common", spell=1152, maxRank=1 },
    { id=38, type="active", level=10, rarity="common", spell=1022, maxRank=1 },
    { id=39, type="active", level=10, rarity="common", spell=633, maxRank=1 },
    { id=40, type="active", level=1, rarity="common", spell=2973, maxRank=1 },
    { id=41, type="active", level=1, rarity="common", spell=1494, maxRank=1 },
    { id=42, type="active", level=4, rarity="common", spell=13163, maxRank=1 },
    { id=43, type="active", level=4, rarity="common", spell=1978, maxRank=1 },
    { id=44, type="active", level=6, rarity="common", spell=3044, maxRank=1 },
    { id=45, type="active", level=6, rarity="common", spell=1130, maxRank=1 },
    { id=46, type="active", level=8, rarity="common", spell=5116, maxRank=1 },
    { id=47, type="active", level=10, rarity="common", spell=13165, maxRank=1 },
    { id=48, type="active", level=10, rarity="common", spell=19883, maxRank=1 },
    { id=49, type="active", level=10, rarity="epic", spell=1515, maxRank=1 },
    { id=50, type="active", level=1, rarity="common", spell=2098, maxRank=1, any={{14,1},{51,1},{53,1}} },
    { id=51, type="active", level=4, rarity="common", spell=53, maxRank=1 },
    { id=53, type="active", level=6, rarity="common", spell=1776, maxRank=1 },
    { id=54, type="active", level=8, rarity="common", spell=5277, maxRank=1 },
    { id=55, type="active", level=10, rarity="common", spell=5171, maxRank=1, any={{14,1},{51,1},{53,1}} },
    { id=56, type="active", level=10, rarity="common", spell=2983, maxRank=1 },
    { id=57, type="active", level=1, rarity="common", spell=2050, maxRank=1 },
    { id=58, type="active", level=1, rarity="common", spell=1243, maxRank=1 },
    { id=59, type="active", level=4, rarity="common", spell=589, maxRank=1 },
    { id=60, type="active", level=6, rarity="common", spell=17, maxRank=1 },
    { id=61, type="active", level=8, rarity="common", spell=586, maxRank=1 },
    { id=62, type="active", level=8, rarity="common", spell=139, maxRank=1 },
    { id=63, type="active", level=10, rarity="common", spell=8092, maxRank=1 },
    { id=64, type="active", level=10, rarity="common", spell=2006, maxRank=1 },
    { id=65, type="active", level=1, rarity="common", spell=8017, maxRank=1 },
    { id=66, type="active", level=4, rarity="common", spell=8042, maxRank=1 },
    { id=67, type="active", level=4, rarity="common", spell=8071, maxRank=1 },
    { id=68, type="active", level=6, rarity="common", spell=2484, maxRank=1 },
    { id=69, type="active", level=8, rarity="common", spell=324, maxRank=1 },
    { id=70, type="active", level=8, rarity="common", spell=5730, maxRank=1 },
    { id=71, type="active", level=10, rarity="common", spell=8050, maxRank=1 },
    { id=72, type="active", level=10, rarity="common", spell=8024, maxRank=1 },
    { id=73, type="active", level=10, rarity="common", spell=3599, maxRank=1 },
    { id=74, type="active", level=10, rarity="common", spell=8075, maxRank=1 },
    { id=75, type="active", level=1, rarity="common", spell=168, maxRank=1 },
    { id=76, type="active", level=4, rarity="common", spell=5504, maxRank=1 },
    { id=77, type="active", level=6, rarity="common", spell=587, maxRank=1 },
    { id=78, type="active", level=6, rarity="common", spell=2136, maxRank=1 },
    { id=79, type="active", level=8, rarity="common", spell=5143, maxRank=1 },
    { id=80, type="active", level=8, rarity="common", spell=118, maxRank=1 },
    { id=81, type="active", level=10, rarity="common", spell=122, maxRank=1 },
    { id=82, type="active", level=1, rarity="common", spell=687, maxRank=1 },
    { id=83, type="active", level=1, rarity="common", spell=348, maxRank=1 },
    { id=84, type="active", level=1, rarity="common", spell=688, maxRank=1 },
    { id=85, type="active", level=4, rarity="common", spell=172, maxRank=1 },
    { id=86, type="active", level=4, rarity="common", spell=702, maxRank=1 },
    { id=87, type="active", level=6, rarity="common", spell=1454, maxRank=1 },
    { id=88, type="active", level=8, rarity="common", spell=980, maxRank=1 },
    { id=89, type="active", level=8, rarity="common", spell=5782, maxRank=1 },
    { id=90, type="active", level=10, rarity="common", spell=1120, maxRank=1 },
    { id=91, type="active", level=10, rarity="common", spell=6201, maxRank=1, all={{90,1}} },
    { id=92, type="active", level=10, rarity="common", spell=697, maxRank=1, all={{90,1}} },
    { id=101, type="talent", level=10, rarity="common", spell=12320, maxRank=5, rankSpells={12320,12852,12853,12855,12856} },
    { id=102, type="talent", level=10, rarity="common", spell=16462, maxRank=5, rankSpells={16462,16463,16464,16465,16466} },
    { id=103, type="talent", level=10, rarity="common", spell=12297, maxRank=5, rankSpells={12297,12750,12751,12752,12753} },
    { id=104, type="talent", level=10, rarity="uncommon", spell=11069, maxRank=5, all={{2,1}}, rankSpells={11069,12338,12339,12340,12341} },
    { id=105, type="talent", level=10, rarity="uncommon", spell=11070, maxRank=5, all={{3,1}}, rankSpells={11070,12473,16763,16765,16766} },
    { id=106, type="talent", level=10, rarity="uncommon", spell=12295, maxRank=3, all={{1,1}}, rankSpells={12295,12676,12677} },
    { id=107, type="talent", level=10, rarity="uncommon", spell=12282, maxRank=3, all={{8,1}}, rankSpells={12282,12663,12664} },
}

local catalogById = {}
for _, card in ipairs(debugCatalog) do
    catalogById[card.id] = card
end

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

local function GetOwnedRank(card)
    local owned = state.sessionRanks[card.id] or 0
    if card.rankSpells then
        for rank, spellId in ipairs(card.rankSpells) do
            if IsKnownSpell(spellId) and rank > owned then
                owned = rank
            end
        end
    elseif IsKnownSpell(card.spell) then
        owned = math.max(owned, 1)
    end
    return owned
end

local function RequirementMet(requirement)
    local card = catalogById[requirement[1]]
    if not card then return false end
    return GetOwnedRank(card) >= (requirement[2] or 1)
end

local function MeetsDebugRequirements(card)
    if card.all then
        for _, requirement in ipairs(card.all) do
            if not RequirementMet(requirement) then
                return false
            end
        end
    end
    if card.any and #card.any > 0 then
        local any = false
        for _, requirement in ipairs(card.any) do
            if RequirementMet(requirement) then
                any = true
                break
            end
        end
        if not any then return false end
    end
    return true
end

local function IsDebugEligible(card)
    if state.destroyedAll[card.id] then
        return false
    end
    local level = UnitLevel("player") or 1
    local sourceCap = math.max(level, INITIAL_ACTIVE_SOURCE_LEVEL_CAP)
    if card.level > sourceCap then
        return false
    end
    if GetOwnedRank(card) >= (card.maxRank or 1) then
        return false
    end
    return MeetsDebugRequirements(card)
end

local debugFrame = CreateFrame("Frame", "AdventurerDraftPoolDebugFrame", UIParent)
debugFrame:SetWidth(760)
debugFrame:SetHeight(475)
debugFrame:SetPoint("CENTER", UIParent, "CENTER", 0, 10)
debugFrame:SetFrameStrata("FULLSCREEN_DIALOG")
debugFrame:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
})
debugFrame:SetBackdropColor(0.04, 0.04, 0.07, 0.98)
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
    for _, card in ipairs(debugCatalog) do
        if card.type == kind and IsDebugEligible(card) then
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
                local rank = GetOwnedRank(card)
                if card.maxRank and card.maxRank > 1 then
                    row.meta:SetText(string.format("Lv%d  %d/%d", card.level, rank + 1, card.maxRank))
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

local function ToggleDebugPool()
    if debugFrame:IsShown() then
        debugFrame:Hide()
    else
        RefreshDebugPool()
        debugFrame:Show()
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
    elseif string.sub(message, 1, 2) == "M|" then
        ParseMeta(message)
    elseif message == "C" then
        ConfirmPendingPick()
        state.destroyed = {}
        for _, button in ipairs(cardButtons) do HideExtraIcons(button) end
        ResetMode()
        RefreshMetaUI()
    elseif string.sub(message, 1, 2) == "E|" then
        state.pendingPickedCardId = nil
        ResetMode()
        RefreshMetaUI()
    end
end)
