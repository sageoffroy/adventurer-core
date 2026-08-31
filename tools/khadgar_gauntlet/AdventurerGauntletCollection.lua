-- Aventureros de Azeroth - Libro de Objetos de cuenta para Gauntlet.
local PREFIX = "AGBOOK"
local FRAME_NAME = "AdventurerGauntletCollectionFrame"
local DISCOVERED = {}
local SORTED = {}
local PAGE = 1
local PER_PAGE = 20

local function SendCommand(command)
    if not UnitName("player") then return end
    SendAddonMessage(PREFIX, command, "WHISPER", UnitName("player"))
end

local frame = CreateFrame("Frame", FRAME_NAME, UIParent, "UIPanelDialogTemplate")
frame:SetWidth(430)
frame:SetHeight(390)
frame:SetPoint("CENTER")
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", function(self) self:StartMoving() end)
frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
frame:Hide()
tinsert(UISpecialFrames, FRAME_NAME)

local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
title:SetPoint("TOP", frame, "TOP", 0, -16)
title:SetText("Libro de Objetos")

local subtitle = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
subtitle:SetPoint("TOP", title, "BOTTOM", 0, -6)
subtitle:SetText("Los objetos aparecen cuando cualquier personaje de la cuenta los descubre.")

local countText = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
countText:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 22, 18)

local pageText = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
pageText:SetPoint("BOTTOM", frame, "BOTTOM", 0, 20)

local slots = {}
for i = 1, PER_PAGE do
    local button = CreateFrame("Button", FRAME_NAME .. "Item" .. i, frame, "ItemButtonTemplate")
    local col = (i - 1) % 5
    local row = math.floor((i - 1) / 5)
    button:SetPoint("TOPLEFT", frame, "TOPLEFT", 45 + col * 68, -78 - row * 66)
    button:SetScript("OnEnter", function(self)
        if not self.entry then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("item:" .. self.entry)
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function() GameTooltip:Hide() end)
    slots[i] = button
end

local prev = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
prev:SetWidth(72)
prev:SetHeight(22)
prev:SetPoint("BOTTOMRIGHT", frame, "BOTTOM", -55, 14)
prev:SetText("Anterior")

local nextButton = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
nextButton:SetWidth(72)
nextButton:SetHeight(22)
nextButton:SetPoint("BOTTOMLEFT", frame, "BOTTOM", 55, 14)
nextButton:SetText("Siguiente")

local function RebuildSorted()
    SORTED = {}
    for entry in pairs(DISCOVERED) do table.insert(SORTED, entry) end
    table.sort(SORTED)
end

local function Refresh()
    RebuildSorted()
    local pages = math.max(1, math.ceil(#SORTED / PER_PAGE))
    if PAGE > pages then PAGE = pages end
    if PAGE < 1 then PAGE = 1 end

    for i = 1, PER_PAGE do
        local button = slots[i]
        local index = (PAGE - 1) * PER_PAGE + i
        local entry = SORTED[index]
        button.entry = entry
        if entry then
            SetItemButtonTexture(button, GetItemIcon(entry) or "Interface\\Icons\\INV_Misc_QuestionMark")
            SetItemButtonCount(button, 0)
            button:Show()
        else
            button:Hide()
        end
    end

    countText:SetText("Descubiertos: " .. #SORTED)
    pageText:SetText("Página " .. PAGE .. " / " .. pages)
    if PAGE > 1 then prev:Enable() else prev:Disable() end
    if PAGE < pages then nextButton:Enable() else nextButton:Disable() end
end

prev:SetScript("OnClick", function()
    if PAGE > 1 then PAGE = PAGE - 1; Refresh() end
end)
nextButton:SetScript("OnClick", function()
    local pages = math.max(1, math.ceil(#SORTED / PER_PAGE))
    if PAGE < pages then PAGE = PAGE + 1; Refresh() end
end)

local function HandleState(message)
    if message == "OPEN" then
        DISCOVERED = {}
        PAGE = 1
        return
    end
    if message == "DONE" then
        Refresh()
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

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("CHAT_MSG_ADDON")
eventFrame:SetScript("OnEvent", function(self, event, ...)
    local prefix, message = ...
    if prefix == PREFIX then HandleState(message) end
end)

SLASH_ADVENTURERGAUNTLETBOOK1 = "/objetos"
SLASH_ADVENTURERGAUNTLETBOOK2 = "/librodeobjetos"
SlashCmdList.ADVENTURERGAUNTLETBOOK = function()
    SendCommand("REFRESH")
end

_G.AdventurerGauntletOpenCollection = function()
    SendCommand("REFRESH")
end
