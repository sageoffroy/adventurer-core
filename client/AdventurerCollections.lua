-- Adventurer talent collection UI.
--
-- Adventurers do not spend native talent points. SpellDraft grants passive
-- talent spells directly, so the stock branching TalentFrame is misleading.
-- The Adventurer collection deliberately mirrors the native 3.3.5 SpellBook
-- presentation: parchment panel, two columns, page navigation and vertical
-- category tabs. Native classes still use Blizzard_TalentUI unchanged.

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
        empty = "Todavía no obtuviste talentos de esta subclase.",
        loading = "Cargando talentos...",
        error = "No se pudo cargar la colección de talentos.",
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
        empty = "You have not acquired talents from this subclass yet.",
        loading = "Loading talents...",
        error = "The talent collection could not be loaded.",
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
local subclassIcons = {
    mercenary = "Interface\\Icons\\Ability_Warrior_OffensiveStance",
    explorer = "Interface\\Icons\\Ability_Hunter_BeastTaming",
    spellcaster = "Interface\\Icons\\Spell_Frost_FrostBolt02",
    illuminated = "Interface\\Icons\\Spell_Holy_HolyBolt",
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

local function AddPanelTexture(name, texture, width, height, point, relativePoint)
    local region = frame:CreateTexture(name, "ARTWORK")
    region:SetTexture(texture)
    region:SetWidth(width)
    region:SetHeight(height)
    region:SetPoint(point, frame, relativePoint or point, 0, 0)
    return region
end

frame.topLeft = AddPanelTexture(
    nil, "Interface\\Spellbook\\UI-SpellbookPanel-TopLeft", 256, 256, "TOPLEFT")
frame.topRight = AddPanelTexture(
    nil, "Interface\\Spellbook\\UI-SpellbookPanel-TopRight", 128, 256, "TOPRIGHT")
frame.botLeft = AddPanelTexture(
    nil, "Interface\\Spellbook\\UI-SpellbookPanel-BotLeft", 256, 256, "BOTTOMLEFT")
frame.botRight = AddPanelTexture(
    nil, "Interface\\Spellbook\\UI-SpellbookPanel-BotRight", 128, 256, "BOTTOMRIGHT")

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
frame.close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -29, -8)
frame.close:SetScript("OnClick", function()
    HideUIPanel(frame)
end)

local state = {
    selected = "mercenary",
    page = 1,
    loading = false,
    error = false,
    items = {
        mercenary = {},
        explorer = {},
        spellcaster = {},
        illuminated = {},
    },
}

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

frame.entries = {}
for index = 1, TALENTS_PER_PAGE do
    local column = index > ROWS_PER_COLUMN and 1 or 0
    local rowIndex = (index - 1) % ROWS_PER_COLUMN

    local entry = CreateFrame("Button", nil, frame)
    entry:SetWidth(150)
    entry:SetHeight(48)
    entry:SetPoint("TOPLEFT", frame, "TOPLEFT", 43 + column * 169, -99 - rowIndex * 57)
    entry:Hide()

    entry.background = entry:CreateTexture(nil, "BACKGROUND")
    entry.background:SetTexture("Interface\\Spellbook\\UI-Spellbook-SpellBackground")
    entry.background:SetWidth(64)
    entry.background:SetHeight(64)
    entry.background:SetPoint("TOPLEFT", entry, "TOPLEFT", -3, 3)

    entry.icon = entry:CreateTexture(nil, "BORDER")
    entry.icon:SetWidth(37)
    entry.icon:SetHeight(37)
    entry.icon:SetPoint("TOPLEFT", entry, "TOPLEFT", 0, 0)

    entry.iconBorder = entry:CreateTexture(nil, "OVERLAY")
    entry.iconBorder:SetTexture("Interface\\Buttons\\UI-Quickslot2")
    entry.iconBorder:SetWidth(64)
    entry.iconBorder:SetHeight(64)
    entry.iconBorder:SetPoint("CENTER", entry.icon, "CENTER", 0, 0)

    entry.highlight = entry:CreateTexture(nil, "HIGHLIGHT")
    entry.highlight:SetTexture("Interface\\Buttons\\ButtonHilight-Square")
    entry.highlight:SetBlendMode("ADD")
    entry.highlight:SetWidth(45)
    entry.highlight:SetHeight(45)
    entry.highlight:SetPoint("CENTER", entry.icon, "CENTER", 0, 0)

    entry.name = entry:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    entry.name:SetWidth(106)
    entry.name:SetHeight(30)
    entry.name:SetPoint("TOPLEFT", entry.icon, "TOPRIGHT", 5, 2)
    entry.name:SetJustifyH("LEFT")
    entry.name:SetJustifyV("TOP")
    entry.name:SetMaxLines(2)

    entry.rank = entry:CreateFontString(nil, "OVERLAY", "SubSpellFont")
    entry.rank:SetWidth(106)
    entry.rank:SetHeight(14)
    entry.rank:SetPoint("BOTTOMLEFT", entry.icon, "BOTTOMRIGHT", 5, 1)
    entry.rank:SetJustifyH("LEFT")

    entry:SetScript("OnEnter", function(self)
        if not self.spellId then
            return
        end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("spell:" .. self.spellId)
        GameTooltip:Show()
    end)
    entry:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    frame.entries[index] = entry
end

frame.empty = frame:CreateFontString(nil, "OVERLAY", "GameFontDisable")
frame.empty:SetWidth(260)
frame.empty:SetPoint("CENTER", frame, "CENTER", -5, 7)
frame.empty:SetJustifyH("CENTER")
frame.empty:SetText("")
frame.empty:Hide()

local function MakePageButton(name, x, nextPage)
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

frame.prev = MakePageButton("AdventurerTalentCollectionPrevPageButton", 50, false)
frame.prev.label = frame.prev:CreateFontString(nil, "OVERLAY", "GameFontNormal")
frame.prev.label:SetText(text.prev)
frame.prev.label:SetPoint("LEFT", frame.prev, "RIGHT", 0, 0)

frame.next = MakePageButton("AdventurerTalentCollectionNextPageButton", 306, true)
frame.next.label = frame.next:CreateFontString(nil, "OVERLAY", "GameFontNormal")
frame.next.label:SetText(text.next)
frame.next.label:SetPoint("RIGHT", frame.next, "LEFT", 0, 0)

local function CreateSubclassTab(index, key)
    local tab = CreateFrame("CheckButton", "AdventurerTalentCollectionTab" .. index, frame)
    tab:SetWidth(32)
    tab:SetHeight(32)
    tab:SetPoint("TOPLEFT", frame, "TOPRIGHT", 2, -78 - (index - 1) * 46)
    tab.subclassKey = key
    tab.tooltip = subclassLabels[key]

    tab.background = tab:CreateTexture(nil, "BACKGROUND")
    tab.background:SetTexture("Interface\\SpellBook\\SpellBook-SkillLineTab")
    tab.background:SetWidth(64)
    tab.background:SetHeight(64)
    tab.background:SetPoint("TOPLEFT", tab, "TOPLEFT", -3, 11)

    tab:SetNormalTexture(subclassIcons[key])
    tab:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")
    tab:SetCheckedTexture("Interface\\Buttons\\CheckButtonHilight", "ADD")

    tab:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(self.tooltip)
        GameTooltip:Show()
    end)
    tab:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
    return tab
end

frame.tabs = {}
for index, key in ipairs(subclassOrder) do
    frame.tabs[index] = CreateSubclassTab(index, key)
end

local function PageCount(items)
    local count = math.ceil(#items / TALENTS_PER_PAGE)
    if count < 1 then
        count = 1
    end
    return count
end

local function RefreshTabs()
    for index, key in ipairs(subclassOrder) do
        frame.tabs[index]:SetChecked(key == state.selected)
    end
end

local function RefreshPage()
    RefreshTabs()

    local items = state.items[state.selected] or {}
    local pageCount = PageCount(items)
    if state.page > pageCount then
        state.page = pageCount
    elseif state.page < 1 then
        state.page = 1
    end

    frame.title:SetText(text.title .. " - " .. subclassLabels[state.selected])
    frame.pageText:SetText(string.format(text.page, state.page))
    frame.prev:SetEnabled(state.page > 1)
    frame.next:SetEnabled(state.page < pageCount)

    local first = (state.page - 1) * TALENTS_PER_PAGE
    for index = 1, TALENTS_PER_PAGE do
        local entry = frame.entries[index]
        local item = items[first + index]
        if item then
            local name, _, icon = GetSpellDisplay(item.spellId)
            entry.spellId = item.spellId
            entry.icon:SetTexture(icon)
            entry.name:SetText(name)
            entry.rank:SetText(string.format(text.rank, item.rank, item.maxRank))
            entry:Show()
        else
            entry.spellId = nil
            entry:Hide()
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

frame.prev:SetScript("OnClick", function()
    if state.page > 1 then
        state.page = state.page - 1
        RefreshPage()
        PlaySound("igAbiliityPageTurn")
    end
end)

frame.next:SetScript("OnClick", function()
    local items = state.items[state.selected] or {}
    if state.page < PageCount(items) then
        state.page = state.page + 1
        RefreshPage()
        PlaySound("igAbiliityPageTurn")
    end
end)

for _, tab in ipairs(frame.tabs) do
    tab:SetScript("OnClick", function(self)
        state.selected = self.subclassKey
        state.page = 1
        RefreshPage()
        PlaySound("igCharacterInfoTab")
    end)
end

local function ResetIncomingCollection()
    for _, key in ipairs(subclassOrder) do
        state.items[key] = {}
    end
    state.page = 1
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
-- alone opens this SpellBook-style collection frame.
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

-- MainMenuBarMicroButtons.xml binds the original function object before this
-- file loads. Rebind the live button so Adventurers route through our wrapper.
if TalentMicroButton then
    TalentMicroButton:SetScript("OnClick", function()
        ToggleTalentFrame()
    end)
end
