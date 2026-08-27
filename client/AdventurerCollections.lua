-- Adventurer acquired-talent collection UI.
--
-- Adventurers receive talents through SpellDraft instead of spending native
-- talent points. Present those acquired talents with the native 3.3.5
-- SpellBook visual language: parchment, two columns, page controls and four
-- bottom tabs for Mercenary, Explorer, Spellcaster and Illuminated.

local ADVENTURER_CLASS_ID = 10
local DRAFT_PREFIX = "AdventurerDraft"
local TALENT_COLLECTION_REQUEST = "ADRAFT_TALENTS"
local TALENTS_PER_PAGE = 12
local ROWS_PER_COLUMN = 6

local locale = GetLocale()
local isSpanish = locale == "esES" or locale == "esMX"

local text
if isSpanish then
    text = {
        title = "Talentos",
        mercenary = "Mercenario",
        explorer = "Explorador",
        spellcaster = "Hechicero",
        illuminated = "Iluminado",
        rank = "Rango %d/%d",
        loading = "Cargando talentos...",
        error = "No se pudo cargar la colección de talentos.",
        empty = "Todavía no obtuviste talentos de esta subclase.",
        page = "Página %d",
        prev = "Ant.",
        next = "Sig.",
    }
else
    text = {
        title = "Talents",
        mercenary = "Mercenary",
        explorer = "Explorer",
        spellcaster = "Spellcaster",
        illuminated = "Illuminated",
        rank = "Rank %d/%d",
        loading = "Loading talents...",
        error = "The talent collection could not be loaded.",
        empty = "You have not acquired talents from this subclass yet.",
        page = "Page %d",
        prev = "Prev",
        next = "Next",
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

local frame
local NativeToggleTalentFrame = ToggleTalentFrame

local function AdventurerToggleTalentFrame()
    if not IsAdventurer() then
        return NativeToggleTalentFrame()
    end

    if UnitLevel("player") < SHOW_TALENT_LEVEL or not frame then
        return
    end

    if PlayerTalentFrame and PlayerTalentFrame:IsShown() then
        HideUIPanel(PlayerTalentFrame)
    end

    if frame:IsShown() then
        HideUIPanel(frame)
    else
        ShowUIPanel(frame)
    end
end

local function RebindTalentEntryPoints()
    ToggleTalentFrame = AdventurerToggleTalentFrame
    if TalentMicroButton then
        TalentMicroButton:SetScript("OnClick", AdventurerToggleTalentFrame)
    end
end

RebindTalentEntryPoints()

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

frame = CreateFrame("Frame", "AdventurerTalentCollectionFrame", UIParent)
frame:SetWidth(384)
frame:SetHeight(512)
frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 0, -104)
frame:SetFrameStrata("HIGH")
frame:EnableMouse(true)
frame:SetClampedToScreen(true)
frame:Hide()

UIPanelWindows["AdventurerTalentCollectionFrame"] = {
    area = "left",
    pushable = 0,
    whileDead = 1,
}

local function AddPanelTexture(texture, width, height, point)
    local region = frame:CreateTexture(nil, "ARTWORK")
    region:SetTexture(texture)
    region:SetWidth(width)
    region:SetHeight(height)
    region:SetPoint(point, frame, point, 0, 0)
    return region
end

frame.topLeft = AddPanelTexture(
    "Interface\\Spellbook\\UI-SpellbookPanel-TopLeft", 256, 256, "TOPLEFT")
frame.topRight = AddPanelTexture(
    "Interface\\Spellbook\\UI-SpellbookPanel-TopRight", 128, 256, "TOPRIGHT")
frame.bottomLeft = AddPanelTexture(
    "Interface\\Spellbook\\UI-SpellbookPanel-BotLeft", 256, 256, "BOTTOMLEFT")
frame.bottomRight = AddPanelTexture(
    "Interface\\Spellbook\\UI-SpellbookPanel-BotRight", 128, 256, "BOTTOMRIGHT")

frame.bookIcon = frame:CreateTexture(nil, "BACKGROUND")
frame.bookIcon:SetTexture("Interface\\Spellbook\\Spellbook-Icon")
frame.bookIcon:SetWidth(58)
frame.bookIcon:SetHeight(58)
frame.bookIcon:SetPoint("TOPLEFT", frame, "TOPLEFT", 10, -8)

frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
frame.title:SetPoint("CENTER", frame, "CENTER", 6, 230)
frame.title:SetText(text.title)

frame.pageText = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
frame.pageText:SetWidth(102)
frame.pageText:SetPoint("BOTTOM", frame, "BOTTOM", -14, 96)
frame.pageText:SetText(string.format(text.page, 1))

frame.close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
frame.close:SetPoint("CENTER", frame, "TOPRIGHT", -44, -25)
frame.close:SetScript("OnClick", function()
    HideUIPanel(frame)
end)

frame.status = frame:CreateFontString(nil, "OVERLAY", "GameFontDisable")
frame.status:SetWidth(250)
frame.status:SetPoint("CENTER", frame, "CENTER", -4, 12)
frame.status:SetJustifyH("CENTER")
frame.status:SetText("")
frame.status:Hide()

local state = {
    selected = "mercenary",
    loading = false,
    error = false,
    pages = {
        mercenary = 1,
        explorer = 1,
        spellcaster = 1,
        illuminated = 1,
    },
    items = {
        mercenary = {},
        explorer = {},
        spellcaster = {},
        illuminated = {},
    },
}

local function SortCollection(items)
    table.sort(items, function(left, right)
        return left.cardId < right.cardId
    end)
end

local function PageCount(items)
    local pages = math.ceil(#items / TALENTS_PER_PAGE)
    if pages < 1 then
        pages = 1
    end
    return pages
end

local function CreateTalentEntry(index)
    local column = index > ROWS_PER_COLUMN and 1 or 0
    local row = (index - 1) % ROWS_PER_COLUMN

    local entry = CreateFrame("Button", "AdventurerTalentCollectionEntry" .. index, frame)
    entry:SetWidth(150)
    entry:SetHeight(48)
    entry:SetPoint("TOPLEFT", frame, "TOPLEFT", 34 + column * 157, -85 - row * 51)
    entry:Show()

    entry.background = entry:CreateTexture(nil, "BACKGROUND")
    entry.background:SetTexture("Interface\\Spellbook\\UI-Spellbook-SpellBackground")
    entry.background:SetWidth(64)
    entry.background:SetHeight(64)
    entry.background:SetPoint("TOPLEFT", entry, "TOPLEFT", -3, 3)

    entry.icon = entry:CreateTexture(nil, "BORDER")
    entry.icon:SetWidth(37)
    entry.icon:SetHeight(37)
    entry.icon:SetPoint("TOPLEFT", entry, "TOPLEFT", 0, 0)
    entry.icon:Hide()

    entry.slot = entry:CreateTexture(nil, "OVERLAY")
    entry.slot:SetTexture("Interface\\Buttons\\UI-Quickslot2")
    entry.slot:SetWidth(64)
    entry.slot:SetHeight(64)
    entry.slot:SetPoint("CENTER", entry.icon, "CENTER", 0, 0)
    entry.slot:Hide()

    entry.highlight = entry:CreateTexture(nil, "HIGHLIGHT")
    entry.highlight:SetTexture("Interface\\Buttons\\ButtonHilight-Square")
    entry.highlight:SetBlendMode("ADD")
    entry.highlight:SetWidth(43)
    entry.highlight:SetHeight(43)
    entry.highlight:SetPoint("CENTER", entry.icon, "CENTER", 0, 0)

    entry.name = entry:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    entry.name:SetWidth(103)
    entry.name:SetPoint("LEFT", entry.icon, "RIGHT", 4, 0)
    entry.name:SetJustifyH("LEFT")
    entry.name:Hide()

    entry.rank = entry:CreateFontString(nil, "OVERLAY", "SubSpellFont")
    entry.rank:SetWidth(79)
    entry.rank:SetHeight(18)
    entry.rank:SetPoint("TOPLEFT", entry.name, "BOTTOMLEFT", 0, 4)
    entry.rank:SetJustifyH("LEFT")
    entry.rank:Hide()

    entry:SetScript("OnEnter", function(self)
        if not self.spellId then
            return
        end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("spell:" .. self.spellId)
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine(string.format(text.rank, self.rankValue or 0, self.maxRank or 0), 1.0, 0.82, 0.0)
        GameTooltip:Show()
    end)
    entry:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    return entry
end

frame.entries = {}
for index = 1, TALENTS_PER_PAGE do
    frame.entries[index] = CreateTalentEntry(index)
end

local function CreatePageButton(name, x, nextPage)
    local button = CreateFrame("Button", name, frame)
    button:SetWidth(32)
    button:SetHeight(32)
    button:SetPoint("CENTER", frame, "BOTTOMLEFT", x, 105)
    if nextPage then
        button:SetNormalTexture("Interface\\Buttons\\UI-SpellbookIcon-NextPage-Up")
        button:SetPushedTexture("Interface\\Buttons\\UI-SpellbookIcon-NextPage-Down")
        button:SetDisabledTexture("Interface\\Buttons\\UI-SpellbookIcon-NextPage-Disabled")
    else
        button:SetNormalTexture("Interface\\Buttons\\UI-SpellbookIcon-PrevPage-Up")
        button:SetPushedTexture("Interface\\Buttons\\UI-SpellbookIcon-PrevPage-Down")
        button:SetDisabledTexture("Interface\\Buttons\\UI-SpellbookIcon-PrevPage-Disabled")
    end
    button:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")
    return button
end

frame.prev = CreatePageButton("AdventurerTalentCollectionPrevPageButton", 50, false)
frame.prevLabel = frame.prev:CreateFontString(nil, "BACKGROUND", "GameFontNormal")
frame.prevLabel:SetText(text.prev)
frame.prevLabel:SetPoint("LEFT", frame.prev, "RIGHT", 0, 0)

frame.next = CreatePageButton("AdventurerTalentCollectionNextPageButton", 314, true)
frame.nextLabel = frame.next:CreateFontString(nil, "BACKGROUND", "GameFontNormal")
frame.nextLabel:SetText(text.next)
frame.nextLabel:SetPoint("RIGHT", frame.next, "LEFT", 0, 0)

local function CreateSubclassTab(index, key)
    local tab = CreateFrame(
        "Button",
        "AdventurerTalentCollectionTab" .. index,
        frame,
        "SpellBookFrameTabButtonTemplate")
    tab:SetWidth(98)
    tab:SetHeight(64)
    tab:SetPoint("CENTER", frame, "BOTTOMLEFT", 50 + (index - 1) * 94, 61)
    tab:SetText(subclassLabels[key])
    tab:SetDisabledTexture("Interface\\SpellBook\\UI-SpellBook-Tab1-Selected")
    tab.subclassKey = key
    tab:Show()

    tab:SetScript("OnClick", function(self)
        state.selected = self.subclassKey
        RefreshPage()
        PlaySound("igCharacterInfoTab")
    end)
    tab:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(subclassLabels[self.subclassKey])
        GameTooltip:Show()
    end)
    tab:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    return tab
end

frame.tabs = {}

local function RefreshTabs()
    for _, key in ipairs(subclassOrder) do
        local tab = frame.tabs[key]
        if tab then
            if key == state.selected then
                tab:Disable()
            else
                tab:Enable()
            end
        end
    end
end

function RefreshPage()
    RefreshTabs()

    local items = state.items[state.selected] or {}
    local pages = PageCount(items)
    local page = state.pages[state.selected] or 1
    if page > pages then
        page = pages
    elseif page < 1 then
        page = 1
    end
    state.pages[state.selected] = page

    frame.pageText:SetText(string.format(text.page, page))

    if page > 1 then
        frame.prev:Enable()
    else
        frame.prev:Disable()
    end
    if page < pages then
        frame.next:Enable()
    else
        frame.next:Disable()
    end

    local first = (page - 1) * TALENTS_PER_PAGE
    for index = 1, TALENTS_PER_PAGE do
        local entry = frame.entries[index]
        local item = items[first + index]
        if item then
            local name, _, icon = GetSpellInfo(item.spellId)
            if not name or name == "" then
                name = "Talent " .. tostring(item.spellId)
            end
            if not icon then
                icon = "Interface\\Icons\\INV_Misc_QuestionMark"
            end

            entry.spellId = item.spellId
            entry.rankValue = item.rank
            entry.maxRank = item.maxRank
            entry.icon:SetTexture(icon)
            entry.name:SetText(name)
            entry.rank:SetText(string.format(text.rank, item.rank, item.maxRank))
            entry.icon:Show()
            entry.slot:Show()
            entry.name:Show()
            entry.rank:Show()
        else
            entry.spellId = nil
            entry.rankValue = nil
            entry.maxRank = nil
            entry.icon:Hide()
            entry.slot:Hide()
            entry.name:Hide()
            entry.rank:Hide()
        end
    end

    if state.loading then
        frame.status:SetText(text.loading)
        frame.status:Show()
    elseif state.error then
        frame.status:SetText(text.error)
        frame.status:Show()
    elseif #items == 0 then
        frame.status:SetText(text.empty)
        frame.status:Show()
    else
        frame.status:Hide()
    end
end

for index, key in ipairs(subclassOrder) do
    frame.tabs[key] = CreateSubclassTab(index, key)
end

frame.prev:SetScript("OnClick", function()
    local page = state.pages[state.selected] or 1
    if page > 1 then
        state.pages[state.selected] = page - 1
        RefreshPage()
        PlaySound("igAbiliityPageTurn")
    end
end)

frame.next:SetScript("OnClick", function()
    local items = state.items[state.selected] or {}
    local page = state.pages[state.selected] or 1
    if page < PageCount(items) then
        state.pages[state.selected] = page + 1
        RefreshPage()
        PlaySound("igAbiliityPageTurn")
    end
end)

local function ResetIncomingCollection()
    for _, key in ipairs(subclassOrder) do
        state.items[key] = {}
        state.pages[key] = 1
    end
    state.loading = true
    state.error = false
end

local function RequestCollection()
    ResetIncomingCollection()
    RefreshPage()
    SendCollectionRequest()
end

frame:SetScript("OnShow", function()
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
        RefreshPage()
        return true
    end

    if fields[2] == "X" then
        state.loading = false
        state.error = true
        RefreshPage()
        return true
    end

    return true
end

local eventFrame = CreateFrame("Frame", "AdventurerTalentCollectionEventFrame", UIParent)
eventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
eventFrame:RegisterEvent("CHAT_MSG_ADDON")
eventFrame:RegisterEvent("SPELLS_CHANGED")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if IsAdventurer() and prefix == DRAFT_PREFIX and message then
            HandleCollectionMessage(message)
        end
        return
    end

    if event == "ADDON_LOADED" then
        local addonName = ...
        if addonName == "Blizzard_TalentUI" then
            RebindTalentEntryPoints()
        end
        return
    end

    if event == "PLAYER_ENTERING_WORLD" then
        RebindTalentEntryPoints()
        if not IsAdventurer() and frame:IsShown() then
            HideUIPanel(frame)
        end
        return
    end

    if event == "SPELLS_CHANGED" and IsAdventurer() and frame:IsShown() and not state.loading then
        RequestCollection()
    end
end)
