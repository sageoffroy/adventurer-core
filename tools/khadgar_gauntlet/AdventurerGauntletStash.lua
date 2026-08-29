-- Adventurer Gauntlet account stash UI for WoW 3.3.5a.
-- Server state arrives through hidden AGSTASH system messages.

local BAG_ITEMS = {}
local STASH_ITEMS = {}
local LEFT_SLOTS = {}
local RIGHT_SLOTS = {}
local MAX_SLOTS = 24

local function SplitProtocol(message)
    local parts = {}
    for token in string.gmatch(message, "[^|]+") do
        table.insert(parts, token)
    end
    return parts
end

local function SendCommand(command)
    if not UnitName("player") then return end
    SendAddonMessage("AGSTASH", command, "WHISPER", UnitName("player"))
end

local frame = CreateFrame("Frame", "AdventurerGauntletStashFrame", UIParent)
frame:SetWidth(590)
frame:SetHeight(300)
frame:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
frame:SetFrameStrata("DIALOG")
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", function(self) self:StartMoving() end)
frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
frame:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 10, right = 10, top = 10, bottom = 10 }
})
frame:Hide()

tinsert(UISpecialFrames, "AdventurerGauntletStashFrame")

local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
title:SetPoint("TOP", frame, "TOP", 0, -16)
title:SetText("Baúl de Expediciones")

local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -7, -7)

local leftLabel = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
leftLabel:SetPoint("TOPLEFT", frame, "TOPLEFT", 32, -48)
leftLabel:SetText("Tu Aventurero")

local rightLabel = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
rightLabel:SetPoint("TOPLEFT", frame, "TOPLEFT", 322, -48)
rightLabel:SetText("Cuenta")

local hint = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
hint:SetPoint("BOTTOM", frame, "BOTTOM", 0, 21)
hint:SetText("Haz clic en un objeto para moverlo al otro lado.")

local depositAll = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
depositAll:SetWidth(110)
depositAll:SetHeight(22)
depositAll:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 31, 15)
depositAll:SetText("Guardar todo")
depositAll:SetScript("OnClick", function() SendCommand("DEPOSITALL") end)

local refresh = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
refresh:SetWidth(82)
refresh:SetHeight(22)
refresh:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -31, 15)
refresh:SetText("Actualizar")
refresh:SetScript("OnClick", function() SendCommand("REFRESH") end)

local function CreatePanel(parent, x)
    local panel = CreateFrame("Frame", nil, parent)
    panel:SetWidth(252)
    panel:SetHeight(178)
    panel:SetPoint("TOPLEFT", parent, "TOPLEFT", x, -69)
    panel:SetBackdrop({
        bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true,
        tileSize = 16,
        edgeSize = 12,
        insets = { left = 3, right = 3, top = 3, bottom = 3 }
    })
    panel:SetBackdropColor(0.03, 0.03, 0.03, 0.86)
    return panel
end

local leftPanel = CreatePanel(frame, 25)
local rightPanel = CreatePanel(frame, 313)

local function CreateSlot(panel, index, side)
    local button = CreateFrame("Button", nil, panel)
    button:SetWidth(36)
    button:SetHeight(36)

    local column = math.mod(index - 1, 6)
    local row = math.floor((index - 1) / 6)
    button:SetPoint("TOPLEFT", panel, "TOPLEFT", 8 + column * 40, -8 - row * 40)

    local background = button:CreateTexture(nil, "BACKGROUND")
    background:SetAllPoints(button)
    background:SetTexture("Interface\\Buttons\\UI-Quickslot2")
    button.background = background

    local icon = button:CreateTexture(nil, "ARTWORK")
    icon:SetPoint("TOPLEFT", button, "TOPLEFT", 3, -3)
    icon:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -3, 3)
    button.icon = icon

    local count = button:CreateFontString(nil, "OVERLAY", "NumberFontNormal")
    count:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -2, 2)
    button.count = count

    button.side = side
    button.entry = nil
    button:EnableMouse(false)

    button:SetScript("OnEnter", function(self)
        if not self.entry then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink("item:" .. self.entry)
        GameTooltip:Show()
    end)

    button:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    button:SetScript("OnClick", function(self)
        if not self.entry then return end
        if self.side == "bag" then
            SendCommand("DEPOSIT|" .. self.entry)
        else
            SendCommand("WITHDRAW|" .. self.entry)
        end
    end)

    return button
end

for index = 1, MAX_SLOTS do
    LEFT_SLOTS[index] = CreateSlot(leftPanel, index, "bag")
    RIGHT_SLOTS[index] = CreateSlot(rightPanel, index, "stash")
end

local function SortedItems(source)
    local items = {}
    for entry, count in pairs(source) do
        if count and count > 0 then
            table.insert(items, { entry = entry, count = count })
        end
    end
    table.sort(items, function(a, b) return a.entry < b.entry end)
    return items
end

local function PaintSlots(slots, source)
    local items = SortedItems(source)
    for index = 1, MAX_SLOTS do
        local button = slots[index]
        local item = items[index]
        if item then
            button.entry = item.entry
            button.icon:SetTexture(GetItemIcon(item.entry) or "Interface\\Icons\\INV_Misc_QuestionMark")
            button.icon:Show()
            button.count:SetText(item.count > 1 and item.count or "")
            button:EnableMouse(true)
        else
            button.entry = nil
            button.icon:SetTexture(nil)
            button.icon:Hide()
            button.count:SetText("")
            button:EnableMouse(false)
        end
    end
end

local function RefreshUI()
    PaintSlots(LEFT_SLOTS, BAG_ITEMS)
    PaintSlots(RIGHT_SLOTS, STASH_ITEMS)
end

local function ResetState()
    BAG_ITEMS = {}
    STASH_ITEMS = {}
end

local function HandleProtocol(message)
    local parts = SplitProtocol(message)
    if parts[1] ~= "AGSTASH" then return end

    local kind = parts[2]
    if kind == "OPEN" then
        ResetState()
        frame:Show()
    elseif kind == "B" then
        local entry = tonumber(parts[3])
        local count = tonumber(parts[4])
        if entry and count then BAG_ITEMS[entry] = count end
    elseif kind == "S" then
        local entry = tonumber(parts[3])
        local count = tonumber(parts[4])
        if entry and count then STASH_ITEMS[entry] = count end
    elseif kind == "DONE" then
        RefreshUI()
        frame:Show()
    end
end

local function SystemMessageFilter(self, event, message, ...)
    if type(message) == "string" and string.sub(message, 1, 8) == "AGSTASH|" then
        HandleProtocol(message)
        return true
    end
    return false, message, ...
end

ChatFrame_AddMessageEventFilter("CHAT_MSG_SYSTEM", SystemMessageFilter)

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("GET_ITEM_INFO_RECEIVED")
eventFrame:SetScript("OnEvent", function()
    if frame:IsShown() then RefreshUI() end
end)
