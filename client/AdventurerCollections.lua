-- Adventurer acquired-talent collection UI.
--
-- Adventurers receive talents through SpellDraft instead of spending native
-- talent points. Present the acquired collection as four permanent branches:
-- Mercenary, Explorer, Spellcaster and Illuminated. Talent names stay out of
-- the layout; the native spell tooltip provides name/description on hover.

local ADVENTURER_CLASS_ID = 10
local DRAFT_PREFIX = "AdventurerDraft"
local TALENT_COLLECTION_REQUEST = "ADRAFT_TALENTS"
local BRANCH_PAGE_SIZE = 24
local GRID_COLUMNS = 4
local GRID_ROWS = 6
local ICON_SIZE = 36

local locale = GetLocale()
local isSpanish = locale == "esES" or locale == "esMX"

local text
if isSpanish then
    text = {
        title = "Talentos",
        summary = "%d talentos obtenidos",
        mercenary = "Mercenario",
        explorer = "Explorador",
        spellcaster = "Hechicero",
        illuminated = "Iluminado",
        rank = "Rango %d/%d",
        loading = "Cargando talentos...",
        error = "No se pudo cargar la colección de talentos.",
        empty = "Todavía no obtuviste talentos.",
    }
else
    text = {
        title = "Talents",
        summary = "%d acquired talents",
        mercenary = "Mercenary",
        explorer = "Explorer",
        spellcaster = "Spellcaster",
        illuminated = "Illuminated",
        rank = "Rank %d/%d",
        loading = "Loading talents...",
        error = "The talent collection could not be loaded.",
        empty = "You have not acquired any talents yet.",
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

ToggleTalentFrame = AdventurerToggleTalentFrame

local function RebindTalentMicroButton()
    if TalentMicroButton then
        TalentMicroButton:SetScript("OnClick", AdventurerToggleTalentFrame)
    end
end

RebindTalentMicroButton()

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
frame:SetWidth(760)
frame:SetHeight(510)
frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 0, -104)
frame:SetFrameStrata("HIGH")
frame:EnableMouse(true)
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
    area = "doublewide",
    pushable = 0,
    whileDead = 1,
}

frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
frame.title:SetPoint("TOP", frame, "TOP", 0, -18)
frame.title:SetText(text.title)

frame.summary = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
frame.summary:SetPoint("TOP", frame.title, "BOTTOM", 0, -5)
frame.summary:SetText("")

frame.close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
frame.close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -6, -6)
frame.close:SetScript("OnClick", function()
    HideUIPanel(frame)
end)

frame.status = frame:CreateFontString(nil, "OVERLAY", "GameFontDisable")
frame.status:SetWidth(500)
frame.status:SetPoint("CENTER", frame, "CENTER", 0, 0)
frame.status:SetJustifyH("CENTER")
frame.status:SetText("")
frame.status:Hide()

local state = {
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

local function TotalTalentCount()
    local total = 0
    for _, key in ipairs(subclassOrder) do
        total = total + #state.items[key]
    end
    return total
end

local function SortCollection(items)
    table.sort(items, function(left, right)
        return left.cardId < right.cardId
    end)
end

local function PageCount(items)
    local pages = math.ceil(#items / BRANCH_PAGE_SIZE)
    if pages < 1 then
        pages = 1
    end
    return pages
end

local function CreateTalentIcon(parent)
    local button = CreateFrame("Button", nil, parent)
    button:SetWidth(ICON_SIZE)
    button:SetHeight(ICON_SIZE)
    button:Hide()

    button.icon = button:CreateTexture(nil, "ARTWORK")
    button.icon:SetAllPoints(button)

    button.slot = button:CreateTexture(nil, "OVERLAY")
    button.slot:SetTexture("Interface\\Buttons\\UI-Quickslot2")
    button.slot:SetWidth(54)
    button.slot:SetHeight(54)
    button.slot:SetPoint("CENTER", button, "CENTER", 0, 0)

    button.highlight = button:CreateTexture(nil, "HIGHLIGHT")
    button.highlight:SetTexture("Interface\\Buttons\\ButtonHilight-Square")
    button.highlight:SetBlendMode("ADD")
    button.highlight:SetAllPoints(button)

    button.rankText = button:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    button.rankText:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", 1, 1)
    button.rankText:SetJustifyH("RIGHT")

    button:SetScript("OnEnter", function(self)
        if not self.spellId then
            return
        end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("spell:" .. self.spellId)
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine(string.format(text.rank, self.rank or 0, self.maxRank or 0), 1.0, 0.82, 0.0)
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    return button
end

local function CreatePageButton(parent, label)
    local button = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    button:SetWidth(24)
    button:SetHeight(20)
    button:SetText(label)
    button:Hide()
    return button
end

local function CreateBranch(index, key)
    local panel = CreateFrame("Frame", "AdventurerTalentCollectionBranch" .. index, frame)
    panel:SetWidth(170)
    panel:SetHeight(410)
    panel:SetPoint("TOPLEFT", frame, "TOPLEFT", 25 + (index - 1) * 178, -68)
    panel:SetBackdrop({
        bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true,
        tileSize = 16,
        edgeSize = 12,
        insets = {left = 3, right = 3, top = 3, bottom = 3},
    })
    panel:SetBackdropColor(0.03, 0.03, 0.04, 0.92)

    panel.headerIcon = panel:CreateTexture(nil, "ARTWORK")
    panel.headerIcon:SetTexture(subclassIcons[key])
    panel.headerIcon:SetWidth(24)
    panel.headerIcon:SetHeight(24)
    panel.headerIcon:SetPoint("TOPLEFT", panel, "TOPLEFT", 9, -9)

    panel.headerIconBorder = panel:CreateTexture(nil, "OVERLAY")
    panel.headerIconBorder:SetTexture("Interface\\Buttons\\UI-Quickslot2")
    panel.headerIconBorder:SetWidth(38)
    panel.headerIconBorder:SetHeight(38)
    panel.headerIconBorder:SetPoint("CENTER", panel.headerIcon, "CENTER", 0, 0)

    panel.title = panel:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    panel.title:SetPoint("LEFT", panel.headerIcon, "RIGHT", 7, 0)
    panel.title:SetWidth(122)
    panel.title:SetJustifyH("LEFT")
    panel.title:SetText(subclassLabels[key])

    panel.icons = {}
    for slot = 1, BRANCH_PAGE_SIZE do
        local column = (slot - 1) % GRID_COLUMNS
        local row = math.floor((slot - 1) / GRID_COLUMNS)
        local icon = CreateTalentIcon(panel)
        icon:SetPoint("TOPLEFT", panel, "TOPLEFT", 9 + column * 39, -52 - row * 51)
        panel.icons[slot] = icon
    end

    panel.prev = CreatePageButton(panel, "<")
    panel.prev:SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 47, 9)

    panel.pageText = panel:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    panel.pageText:SetWidth(44)
    panel.pageText:SetPoint("BOTTOM", panel, "BOTTOM", 0, 14)
    panel.pageText:SetJustifyH("CENTER")
    panel.pageText:Hide()

    panel.next = CreatePageButton(panel, ">")
    panel.next:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -47, 9)

    panel.key = key
    return panel
end

frame.branches = {}
for index, key in ipairs(subclassOrder) do
    frame.branches[key] = CreateBranch(index, key)
end

local function RefreshBranch(key)
    local panel = frame.branches[key]
    local items = state.items[key]
    local pages = PageCount(items)
    local page = state.pages[key]

    if page > pages then
        page = pages
    elseif page < 1 then
        page = 1
    end
    state.pages[key] = page

    panel.title:SetText(subclassLabels[key] .. " (" .. #items .. ")")

    local first = (page - 1) * BRANCH_PAGE_SIZE
    for slot = 1, BRANCH_PAGE_SIZE do
        local button = panel.icons[slot]
        local item = items[first + slot]
        if item then
            local _, _, icon = GetSpellInfo(item.spellId)
            if not icon then
                icon = "Interface\\Icons\\INV_Misc_QuestionMark"
            end
            button.spellId = item.spellId
            button.rank = item.rank
            button.maxRank = item.maxRank
            button.icon:SetTexture(icon)
            button.rankText:SetText(item.rank .. "/" .. item.maxRank)
            button:Show()
        else
            button.spellId = nil
            button.rank = nil
            button.maxRank = nil
            button:Hide()
        end
    end

    if pages > 1 then
        panel.prev:Show()
        panel.next:Show()
        panel.pageText:SetText(page .. "/" .. pages)
        panel.pageText:Show()
        panel.prev:SetEnabled(page > 1)
        panel.next:SetEnabled(page < pages)
    else
        panel.prev:Hide()
        panel.next:Hide()
        panel.pageText:Hide()
    end
end

local function RefreshCollection()
    frame.summary:SetText(string.format(text.summary, TotalTalentCount()))
    for _, key in ipairs(subclassOrder) do
        RefreshBranch(key)
    end

    if state.loading then
        frame.status:SetText(text.loading)
        frame.status:Show()
    elseif state.error then
        frame.status:SetText(text.error)
        frame.status:Show()
    elseif TotalTalentCount() == 0 then
        frame.status:SetText(text.empty)
        frame.status:Show()
    else
        frame.status:Hide()
    end
end

for _, key in ipairs(subclassOrder) do
    local branchKey = key
    local panel = frame.branches[branchKey]
    panel.prev:SetScript("OnClick", function()
        if state.pages[branchKey] > 1 then
            state.pages[branchKey] = state.pages[branchKey] - 1
            RefreshBranch(branchKey)
            PlaySound("igAbiliityPageTurn")
        end
    end)
    panel.next:SetScript("OnClick", function()
        local pages = PageCount(state.items[branchKey])
        if state.pages[branchKey] < pages then
            state.pages[branchKey] = state.pages[branchKey] + 1
            RefreshBranch(branchKey)
            PlaySound("igAbiliityPageTurn")
        end
    end)
end

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
    RefreshCollection()
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
        RefreshCollection()
        return true
    end

    if fields[2] == "X" then
        state.loading = false
        state.error = true
        RefreshCollection()
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
            RebindTalentMicroButton()
        end
        return
    end

    if event == "PLAYER_ENTERING_WORLD" then
        RebindTalentMicroButton()
        if not IsAdventurer() and frame:IsShown() then
            HideUIPanel(frame)
        end
        return
    end

    if event == "SPELLS_CHANGED" and IsAdventurer() and frame:IsShown() and not state.loading then
        RequestCollection()
    end
end)
