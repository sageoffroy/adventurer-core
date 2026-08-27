-- Adventurer talent collection UI.
--
-- Adventurers do not spend native talent points. SpellDraft grants passive
-- talent spells directly, so the stock branching TalentFrame is misleading.
-- This frame replaces only the Adventurer's ToggleTalentFrame entry point and
-- displays the passive talents actually known by the current character.

local ADVENTURER_CLASS_ID = 10
local DRAFT_PREFIX = "AdventurerDraft"
local TALENT_COLLECTION_REQUEST = "ADRAFT_TALENTS"
local VISIBLE_ROWS = 8
local ROW_HEIGHT = 45

local locale = GetLocale()
local isSpanish = locale == "esES" or locale == "esMX"

local text
if isSpanish then
    text = {
        title = "Talentos",
        subtitle = "Talentos obtenidos",
        mercenary = "Mercenario",
        explorer = "Explorador",
        spellcaster = "Hechicero",
        illuminated = "Iluminado",
        rank = "Rango %d/%d",
        empty = "Todavía no obtuviste talentos de esta subclase.",
        loading = "Cargando talentos...",
        error = "No se pudo cargar la colección de talentos.",
        total = "%d talentos obtenidos",
    }
else
    text = {
        title = "Talents",
        subtitle = "Acquired talents",
        mercenary = "Mercenary",
        explorer = "Explorer",
        spellcaster = "Spellcaster",
        illuminated = "Illuminated",
        rank = "Rank %d/%d",
        empty = "You have not acquired talents from this subclass yet.",
        loading = "Loading talents...",
        error = "The talent collection could not be loaded.",
        total = "%d acquired talents",
    }
end

local subclassOrder = {"mercenary", "explorer", "spellcaster", "illuminated"}
local subclassLabels = {
    mercenary = text.mercenary,
    explorer = text.explorer,
    spellcaster = text.spellcaster,
    illuminated = text.illuminated,
}

local function IsAdventurer()
    local className, classToken, classId = UnitClass("player")
    if classId == ADVENTURER_CLASS_ID or classToken == "ADVENTURER" then
        return true
    end
    return className == "Adventurer" or className == "Aventurero" or className == "Aventurera"
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

local function SendCollectionRequest()
    local target = UnitName("player")
    if target and target ~= "" then
        SendChatMessage(TALENT_COLLECTION_REQUEST, "WHISPER", nil, target)
    end
end

local function CollectionWhisperFilter(_, _, message, sender)
    if not IsAdventurer() or sender ~= UnitName("player") then
        return false
    end
    return message == TALENT_COLLECTION_REQUEST
end

ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER", CollectionWhisperFilter)
ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER_INFORM", CollectionWhisperFilter)

if RegisterAddonMessagePrefix then
    RegisterAddonMessagePrefix(DRAFT_PREFIX)
end

local frame = CreateFrame("Frame", "AdventurerTalentCollectionFrame", UIParent)
frame:SetWidth(420)
frame:SetHeight(510)
frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 0, -104)
frame:SetFrameStrata("HIGH")
frame:EnableMouse(true)
frame:SetMovable(false)
frame:SetClampedToScreen(true)
frame:Hide()
frame:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = {left = 11, right = 12, top = 12, bottom = 11},
})

UIPanelWindows["AdventurerTalentCollectionFrame"] = {
    area = "left",
    pushable = 6,
    whileDead = 1,
}

frame.portrait = frame:CreateTexture(nil, "ARTWORK")
frame.portrait:SetWidth(58)
frame.portrait:SetHeight(58)
frame.portrait:SetPoint("TOPLEFT", frame, "TOPLEFT", 15, -14)

frame.portraitBorder = frame:CreateTexture(nil, "OVERLAY")
frame.portraitBorder:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
frame.portraitBorder:SetWidth(78)
frame.portraitBorder:SetHeight(78)
frame.portraitBorder:SetPoint("CENTER", frame.portrait, "CENTER", 10, -10)

frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
frame.title:SetPoint("TOP", frame, "TOP", 0, -20)
frame.title:SetText(text.title)

frame.subtitle = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
frame.subtitle:SetPoint("TOP", frame.title, "BOTTOM", 0, -8)
frame.subtitle:SetText(text.subtitle)

frame.summary = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
frame.summary:SetPoint("TOP", frame.subtitle, "BOTTOM", 0, -5)
frame.summary:SetText("")

frame.close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
frame.close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -6, -6)
frame.close:SetScript("OnClick", function()
    HideUIPanel(frame)
end)

frame.body = CreateFrame("Frame", nil, frame)
frame.body:SetPoint("TOPLEFT", frame, "TOPLEFT", 24, -92)
frame.body:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -34, 58)
frame.body:SetBackdrop({
    bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
    edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
    tile = true,
    tileSize = 16,
    edgeSize = 12,
    insets = {left = 3, right = 3, top = 3, bottom = 3},
})
frame.body:SetBackdropColor(0.03, 0.03, 0.04, 0.85)

local state = {
    selected = "mercenary",
    loading = false,
    error = false,
    items = {
        mercenary = {},
        explorer = {},
        spellcaster = {},
        illuminated = {},
    },
}

frame.rows = {}
for index = 1, VISIBLE_ROWS do
    local row = CreateFrame("Button", nil, frame.body)
    row:SetHeight(ROW_HEIGHT - 2)
    row:SetPoint("TOPLEFT", frame.body, "TOPLEFT", 8, -8 - (index - 1) * ROW_HEIGHT)
    row:SetPoint("RIGHT", frame.body, "RIGHT", -20, 0)
    row:Hide()

    row.highlight = row:CreateTexture(nil, "HIGHLIGHT")
    row.highlight:SetTexture("Interface\\QuestFrame\\UI-QuestTitleHighlight")
    row.highlight:SetBlendMode("ADD")
    row.highlight:SetAllPoints(row)

    row.icon = row:CreateTexture(nil, "ARTWORK")
    row.icon:SetWidth(36)
    row.icon:SetHeight(36)
    row.icon:SetPoint("LEFT", row, "LEFT", 4, 0)

    row.iconBorder = row:CreateTexture(nil, "OVERLAY")
    row.iconBorder:SetTexture("Interface\\Buttons\\UI-Quickslot2")
    row.iconBorder:SetWidth(54)
    row.iconBorder:SetHeight(54)
    row.iconBorder:SetPoint("CENTER", row.icon, "CENTER", 0, 0)

    row.name = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    row.name:SetPoint("TOPLEFT", row.icon, "TOPRIGHT", 9, -3)
    row.name:SetPoint("RIGHT", row, "RIGHT", -4, 0)
    row.name:SetJustifyH("LEFT")

    row.rank = row:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    row.rank:SetPoint("BOTTOMLEFT", row.icon, "BOTTOMRIGHT", 9, 3)
    row.rank:SetPoint("RIGHT", row, "RIGHT", -4, 0)
    row.rank:SetJustifyH("LEFT")

    row:SetScript("OnEnter", function(self)
        if not self.spellId then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("spell:" .. self.spellId)
        GameTooltip:Show()
    end)
    row:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    frame.rows[index] = row
end

frame.scroll = CreateFrame("ScrollFrame", "AdventurerTalentCollectionScrollFrame", frame.body, "FauxScrollFrameTemplate")
frame.scroll:SetPoint("TOPLEFT", frame.body, "TOPLEFT", 0, -4)
frame.scroll:SetPoint("BOTTOMRIGHT", frame.body, "BOTTOMRIGHT", -4, 4)

frame.empty = frame.body:CreateFontString(nil, "OVERLAY", "GameFontDisable")
frame.empty:SetPoint("CENTER", frame.body, "CENTER", 0, 0)
frame.empty:SetWidth(300)
frame.empty:SetJustifyH("CENTER")
frame.empty:SetText("")

frame.tabs = {}
for index, key in ipairs(subclassOrder) do
    local tab = CreateFrame("Button", "AdventurerTalentCollectionTab" .. index, frame, "CharacterFrameTabButtonTemplate")
    tab:SetID(index)
    tab:SetText(subclassLabels[key])
    tab:SetWidth(94)
    tab:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 17 + (index - 1) * 96, 16)
    tab.subclassKey = key
    frame.tabs[index] = tab
end

local function GetSpellDisplay(spellId)
    local name, rank, icon = GetSpellInfo(spellId)
    if not name or name == "" then
        name = "Talent " .. tostring(spellId)
    end
    if not icon then
        icon = "Interface\\Icons\\INV_Misc_QuestionMark"
    end
    return name, rank, icon
end

local function SortCollection(items)
    table.sort(items, function(left, right)
        local leftName = GetSpellInfo(left.spellId) or ""
        local rightName = GetSpellInfo(right.spellId) or ""
        if leftName == rightName then
            return left.cardId < right.cardId
        end
        return leftName < rightName
    end)
end

local function TotalTalentCount()
    local total = 0
    for _, key in ipairs(subclassOrder) do
        total = total + #state.items[key]
    end
    return total
end

local function RefreshTabs()
    for index, key in ipairs(subclassOrder) do
        local tab = frame.tabs[index]
        local count = #state.items[key]
        tab:SetText(subclassLabels[key] .. " (" .. count .. ")")
        if key == state.selected then
            PanelTemplates_SelectTab(tab)
        else
            PanelTemplates_DeselectTab(tab)
        end
    end
end

local function RefreshRows()
    RefreshTabs()
    frame.summary:SetText(string.format(text.total, TotalTalentCount()))

    local items = state.items[state.selected] or {}
    local offset = FauxScrollFrame_GetOffset(frame.scroll)
    FauxScrollFrame_Update(frame.scroll, #items, VISIBLE_ROWS, ROW_HEIGHT)

    for index = 1, VISIBLE_ROWS do
        local row = frame.rows[index]
        local item = items[offset + index]
        if item then
            local name, _, icon = GetSpellDisplay(item.spellId)
            row.spellId = item.spellId
            row.icon:SetTexture(icon)
            row.name:SetText(name)
            row.rank:SetText(string.format(text.rank, item.rank, item.maxRank))
            row:Show()
        else
            row.spellId = nil
            row:Hide()
        end
    end

    if state.loading then
        frame.empty:SetText(text.loading)
        frame.empty:Show()
    elseif state.error then
        frame.empty:SetText(text.error)
        frame.empty:Show()
    elseif #items == 0 then
        frame.empty:SetText(text.empty)
        frame.empty:Show()
    else
        frame.empty:Hide()
    end
end

frame.scroll:SetScript("OnVerticalScroll", function(self, offset)
    FauxScrollFrame_OnVerticalScroll(self, offset, ROW_HEIGHT, RefreshRows)
end)

for _, tab in ipairs(frame.tabs) do
    tab:SetScript("OnClick", function(self)
        state.selected = self.subclassKey
        FauxScrollFrame_SetOffset(frame.scroll, 0)
        frame.scroll:SetVerticalScroll(0)
        RefreshRows()
        PlaySound("igCharacterInfoTab")
    end)
end

local function ResetIncomingCollection()
    for _, key in ipairs(subclassOrder) do
        state.items[key] = {}
    end
    state.loading = true
    state.error = false
end

local function RequestCollection()
    ResetIncomingCollection()
    RefreshRows()
    SendCollectionRequest()
end

frame:SetScript("OnShow", function()
    SetPortraitTexture(frame.portrait, "player")
    RequestCollection()
end)

frame:SetScript("OnHide", function()
    GameTooltip:Hide()
end)

local function HandleCollectionMessage(message)
    local fields = SplitText(message, "|")
    if fields[1] ~= "T" then
        return false
    end

    if fields[2] == "B" then
        ResetIncomingCollection()
        return true
    end

    if fields[2] == "C" then
        local cardId = tonumber(fields[3] or "")
        local subclass = fields[4]
        local rank = tonumber(fields[5] or "")
        local maxRank = tonumber(fields[6] or "")
        local spellId = tonumber(fields[7] or "")
        if cardId and subclass and state.items[subclass] and rank and maxRank and spellId then
            table.insert(state.items[subclass], {
                cardId = cardId,
                rank = rank,
                maxRank = maxRank,
                spellId = spellId,
            })
        end
        return true
    end

    if fields[2] == "E" then
        state.loading = false
        state.error = false
        for _, key in ipairs(subclassOrder) do
            SortCollection(state.items[key])
        end
        RefreshRows()
        return true
    end

    if fields[2] == "X" then
        state.loading = false
        state.error = true
        RefreshRows()
        return true
    end

    return true
end

local eventFrame = CreateFrame("Frame", "AdventurerTalentCollectionEventFrame", UIParent)
eventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
eventFrame:RegisterEvent("CHAT_MSG_ADDON")
eventFrame:RegisterEvent("SPELLS_CHANGED")
eventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if IsAdventurer() and prefix == DRAFT_PREFIX and message then
            HandleCollectionMessage(message)
        end
        return
    end

    if event == "PLAYER_ENTERING_WORLD" then
        if not IsAdventurer() and frame:IsShown() then
            HideUIPanel(frame)
        end
        return
    end

    if event == "SPELLS_CHANGED" and IsAdventurer() and frame:IsShown() and not state.loading then
        RequestCollection()
    end
end)

-- Keep the stock talent window untouched for every native class. The Adventurer
-- alone opens the collection frame, so Blizzard_TalentUI never needs invasive
-- hooks or a replacement Talent.dbc presentation layer.
local NativeToggleTalentFrame = ToggleTalentFrame
function ToggleTalentFrame()
    if not IsAdventurer() then
        return NativeToggleTalentFrame()
    end

    if UnitLevel("player") < SHOW_TALENT_LEVEL then
        return
    end

    if frame:IsShown() then
        HideUIPanel(frame)
    else
        ShowUIPanel(frame)
    end
end
