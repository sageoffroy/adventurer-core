-- Adventurer Gauntlet account item collection for WoW 3.3.5a.
local PREFIX = "AGBOOK"
local DISCOVERED = {}
local PAGE_SIZE = 12
local currentPage = 1
local rows = {}

local function SendCommand(command)
    if not UnitName("player") then return end
    SendAddonMessage(PREFIX, command, "WHISPER", UnitName("player"))
end

local frame = CreateFrame("Frame", "AdventurerGauntletBookFrame", UIParent)
frame:SetWidth(430)
frame:SetHeight(430)
frame:SetPoint("CENTER")
frame:SetFrameStrata("DIALOG")
frame:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 },
})
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", function(self) self:StartMoving() end)
frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
frame:Hide()
tinsert(UISpecialFrames, "AdventurerGauntletBookFrame")

local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
title:SetPoint("TOP", 0, -24)
title:SetText("Libro de Objetos")

local subtitle = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
subtitle:SetPoint("TOP", title, "BOTTOM", 0, -6)
subtitle:SetText("Objetos descubiertos por todos tus aventureros")

local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
close:SetPoint("TOPRIGHT", -5, -5)

local pageText = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
pageText:SetPoint("BOTTOM", 0, 24)

local prev = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
prev:SetWidth(80)
prev:SetHeight(22)
prev:SetPoint("BOTTOMLEFT", 24, 18)
prev:SetText("Anterior")

local nextButton = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
nextButton:SetWidth(80)
nextButton:SetHeight(22)
nextButton:SetPoint("BOTTOMRIGHT", -24, 18)
nextButton:SetText("Siguiente")

for i = 1, PAGE_SIZE do
    local row = CreateFrame("Button", nil, frame)
    row:SetWidth(180)
    row:SetHeight(48)
    local column = i > 6 and 2 or 1
    local position = ((i - 1) % 6)
    row:SetPoint("TOPLEFT", column == 1 and 24 or 224, -70 - position * 52)

    row.icon = row:CreateTexture(nil, "ARTWORK")
    row.icon:SetWidth(40)
    row.icon:SetHeight(40)
    row.icon:SetPoint("LEFT", 2, 0)

    row.name = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    row.name:SetPoint("LEFT", row.icon, "RIGHT", 8, 0)
    row.name:SetWidth(125)
    row.name:SetJustifyH("LEFT")

    row:SetScript("OnEnter", function(self)
        if not self.entry then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("item:" .. self.entry)
        GameTooltip:Show()
    end)
    row:SetScript("OnLeave", function() GameTooltip:Hide() end)
    rows[i] = row
end

local function OrderedEntries()
    local result = {}
    for entry in pairs(DISCOVERED) do table.insert(result, entry) end
    table.sort(result)
    return result
end

local function RefreshUI()
    local entries = OrderedEntries()
    local pages = math.max(1, math.ceil(#entries / PAGE_SIZE))
    if currentPage > pages then currentPage = pages end
    if currentPage < 1 then currentPage = 1 end

    for i = 1, PAGE_SIZE do
        local index = (currentPage - 1) * PAGE_SIZE + i
        local entry = entries[index]
        local row = rows[i]
        row.entry = entry
        if entry then
            local name = GetItemInfo(entry) or ("Objeto " .. entry)
            row.icon:SetTexture(GetItemIcon(entry) or "Interface\\Icons\\INV_Misc_QuestionMark")
            row.name:SetText(name)
            row:Show()
        else
            row:Hide()
        end
    end

    pageText:SetText(string.format("Descubiertos: %d   Página %d/%d", #entries, currentPage, pages))
    prev:SetEnabled(currentPage > 1)
    nextButton:SetEnabled(currentPage < pages)
end

prev:SetScript("OnClick", function()
    currentPage = currentPage - 1
    RefreshUI()
end)
nextButton:SetScript("OnClick", function()
    currentPage = currentPage + 1
    RefreshUI()
end)

local function HandleState(message)
    if message == "OPEN" then
        DISCOVERED = {}
        currentPage = 1
        frame:Show()
        return
    end
    if message == "DONE" then
        RefreshUI()
        frame:Show()
        return
    end
    local entry = string.match(message, "^I|(%d+)$")
    if entry then DISCOVERED[tonumber(entry)] = true end
end

local function SystemMessageFilter(self, event, message, ...)
    if type(message) ~= "string" or string.sub(message, 1, 7) ~= "AGBOOK|" then
        return false, message, ...
    end
    HandleState(string.sub(message, 8))
    return true
end
ChatFrame_AddMessageEventFilter("CHAT_MSG_SYSTEM", SystemMessageFilter)

SLASH_ADVENTURERGAUNTLETBOOK1 = "/libro"
SLASH_ADVENTURERGAUNTLETBOOK2 = "/objetos"
SlashCmdList["ADVENTURERGAUNTLETBOOK"] = function()
    SendCommand("REFRESH")
end
