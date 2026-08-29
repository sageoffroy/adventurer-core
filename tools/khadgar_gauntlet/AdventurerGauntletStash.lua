-- Adventurer Gauntlet account stash UI for WoW 3.3.5a.
-- A single account bank: drag equipment in, click stored items to withdraw.

local STASH_ITEMS = {}
local SLOTS = {}
local MAX_SLOTS = 49
local COLUMNS = 7
local PREFIX = "AGSTASH"

local function SendCommand(command)
    if not UnitName("player") then return end
    SendAddonMessage(PREFIX, command, "WHISPER", UnitName("player"))
end

local frame = CreateFrame("Frame", "AdventurerGauntletStashFrame", UIParent)
frame:SetWidth(356)
frame:SetHeight(382)
frame:SetPoint("CENTER", UIParent, "CENTER", 0, 35)
frame:SetFrameStrata("DIALOG")
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", function(self)
    if not CursorHasItem() then self:StartMoving() end
end)
frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
frame:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 32,
    insets = { left = 11, right = 11, top = 11, bottom = 11 }
})
frame:Hide()

tinsert(UISpecialFrames, "AdventurerGauntletStashFrame")

local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
title:SetPoint("TOP", frame, "TOP", 0, -17)
title:SetText("Baúl de Expediciones")

local subtitle = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
subtitle:SetPoint("TOP", title, "BOTTOM", 0, -6)
subtitle:SetText("Todo lo que guardes aquí sobrevive a la muerte")

local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -7, -7)

local panel = CreateFrame("Frame", nil, frame)
panel:SetWidth(310)
panel:SetHeight(310)
panel:SetPoint("TOP", frame, "TOP", 0, -62)
panel:SetBackdrop({
    bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
    edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
    tile = true,
    tileSize = 16,
    edgeSize = 12,
    insets = { left = 4, right = 4, top = 4, bottom = 4 }
})
panel:SetBackdropColor(0.08, 0.06, 0.03, 0.96)
panel:SetBackdropBorderColor(0.55, 0.43, 0.24, 1.0)
panel:EnableMouse(true)

local hint = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
hint:SetPoint("BOTTOM", frame, "BOTTOM", 0, 13)
hint:SetText("Arrastra equipo para guardar · Clic para retirar")

local function CursorItemEntry()
    local cursorType, itemID = GetCursorInfo()
    if cursorType == "item" then
        return tonumber(itemID)
    end
    return nil
end

local function TryDepositCursorItem()
    local entry = CursorItemEntry()
    if not entry then return false end

    -- ClearCursor only cancels the client's pickup. The server validates that the
    -- item is equipable and removes exactly one real item if the deposit succeeds.
    ClearCursor()
    SendCommand("DEPOSIT|" .. entry)
    return true
end

panel:SetScript("OnReceiveDrag", TryDepositCursorItem)
panel:SetScript("OnMouseUp", function()
    if CursorHasItem() then TryDepositCursorItem() end
end)

local function CreateSlot(index)
    local name = "AdventurerGauntletStashSlot" .. index
    local button = CreateFrame("Button", name, panel, "ItemButtonTemplate")
    button:SetWidth(38)
    button:SetHeight(38)

    local column = (index - 1) % COLUMNS
    local row = math.floor((index - 1) / COLUMNS)
    button:SetPoint("TOPLEFT", panel, "TOPLEFT", 10 + column * 42, -10 - row * 42)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")

    button.icon = _G[name .. "IconTexture"]
    button.count = _G[name .. "Count"]

    -- The stock quickslot art has a small dark center. Add our own dark fill under
    -- it so the EMPTY slot has exactly the same visible area as an item icon.
    local slotFill = button:CreateTexture(nil, "BACKGROUND")
    slotFill:SetTexture(0.015, 0.015, 0.015, 0.95)
    slotFill:SetPoint("TOPLEFT", button, "TOPLEFT", 2, -2)
    slotFill:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -2, 2)
    button.slotFill = slotFill

    if button.icon then
        button.icon:ClearAllPoints()
        button.icon:SetPoint("TOPLEFT", button, "TOPLEFT", 2, -2)
        button.icon:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -2, 2)
        button.icon:Hide()
    end

    local normal = button:GetNormalTexture()
    if normal then
        normal:SetTexture("Interface\\Buttons\\UI-Quickslot2")
        normal:ClearAllPoints()
        normal:SetAllPoints(button)
    end

    local highlight = button:GetHighlightTexture()
    if highlight then
        highlight:SetTexture("Interface\\Buttons\\ButtonHilight-Square")
        highlight:SetBlendMode("ADD")
        highlight:ClearAllPoints()
        highlight:SetPoint("TOPLEFT", button, "TOPLEFT", 2, -2)
        highlight:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -2, 2)
    end

    if button.count then button.count:SetText("") end

    button.entry = nil

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
        if CursorHasItem() then
            TryDepositCursorItem()
            return
        end
        if self.entry then
            SendCommand("WITHDRAW|" .. self.entry)
        end
    end)

    button:SetScript("OnReceiveDrag", function()
        TryDepositCursorItem()
    end)

    return button
end

for index = 1, MAX_SLOTS do
    SLOTS[index] = CreateSlot(index)
end

local function SortedItems()
    local items = {}
    for entry, count in pairs(STASH_ITEMS) do
        if count and count > 0 then
            table.insert(items, { entry = entry, count = count })
        end
    end
    table.sort(items, function(a, b) return a.entry < b.entry end)
    return items
end

local function PaintItem(button, item)
    button.entry = item and item.entry or nil

    if not item then
        if button.icon then
            button.icon:SetTexture(nil)
            button.icon:Hide()
        end
        if button.count then button.count:SetText("") end
        if SetItemButtonQuality then SetItemButtonQuality(button, nil) end
        return
    end

    local texture = GetItemIcon(item.entry) or "Interface\\Icons\\INV_Misc_QuestionMark"
    if button.icon then
        button.icon:SetTexture(texture)
        button.icon:Show()
    elseif SetItemButtonTexture then
        SetItemButtonTexture(button, texture)
    end

    if button.count then
        button.count:SetText(item.count > 1 and item.count or "")
    elseif SetItemButtonCount then
        SetItemButtonCount(button, item.count)
    end

    if SetItemButtonQuality then
        local _, _, quality = GetItemInfo(item.entry)
        SetItemButtonQuality(button, quality, item.entry)
    end
end

local function RefreshUI()
    local items = SortedItems()
    for index = 1, MAX_SLOTS do
        PaintItem(SLOTS[index], items[index])
    end
end

local function HandleState(message)
    if message == "OPEN" then
        STASH_ITEMS = {}
        frame:Show()
        return
    end

    if message == "DONE" then
        RefreshUI()
        frame:Show()
        return
    end

    local entry, count = string.match(message, "^S|(%d+)|(%d+)$")
    if entry and count then
        STASH_ITEMS[tonumber(entry)] = tonumber(count)
    end
end

-- Current server builds the snapshot through system messages. Consume them here so
-- the transport stays invisible to the player.
local function SystemMessageFilter(self, event, message, ...)
    if type(message) ~= "string" or string.sub(message, 1, 8) ~= "AGSTASH|" then
        return false, message, ...
    end

    local payload = string.sub(message, 9)
    if payload == "OPEN" or payload == "DONE" then
        HandleState(payload)
    else
        local kind, entry, count = string.match(payload, "^([BS])|(%d+)|(%d+)$")
        if kind == "S" and entry and count then
            HandleState("S|" .. entry .. "|" .. count)
        end
    end

    return true
end

ChatFrame_AddMessageEventFilter("CHAT_MSG_SYSTEM", SystemMessageFilter)

-- Also understand hidden addon-channel snapshots if the server transport changes.
local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("CHAT_MSG_ADDON")
eventFrame:RegisterEvent("GET_ITEM_INFO_RECEIVED")
eventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if prefix == PREFIX then
            HandleState(message)
        end
    elseif event == "GET_ITEM_INFO_RECEIVED" and frame:IsShown() then
        RefreshUI()
    end
end)
