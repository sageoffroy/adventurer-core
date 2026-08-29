-- Adventurer Gauntlet account stash UI for WoW 3.3.5a.
-- Uses Blizzard's native BankFrame artwork while keeping account-level stash logic.

local STASH_ITEMS = {}
local SLOTS = {}
local MAX_SLOTS = 28
local COLUMNS = 7
local PREFIX = "AGSTASH"

local function SendCommand(command)
    if not UnitName("player") then return end
    SendAddonMessage(PREFIX, command, "WHISPER", UnitName("player"))
end

local frame = CreateFrame("Frame", "AdventurerGauntletStashFrame", UIParent)
frame:SetWidth(384)
frame:SetHeight(302)
frame:SetPoint("CENTER", UIParent, "CENTER", -150, 45)
frame:SetFrameStrata("DIALOG")
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", function(self)
    if not CursorHasItem() then self:StartMoving() end
end)
frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
frame:Hide()

tinsert(UISpecialFrames, "AdventurerGauntletStashFrame")

-- The upper half of Blizzard's bank artwork already contains the 7x4 item-slot grid.
local topLeft = frame:CreateTexture(nil, "BORDER")
topLeft:SetTexture("Interface\\BankFrame\\UI-BankFrame-TopLeft")
topLeft:SetWidth(256)
topLeft:SetHeight(256)
topLeft:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)

local topRight = frame:CreateTexture(nil, "BORDER")
topRight:SetTexture("Interface\\BankFrame\\UI-BankFrame-TopRight")
topRight:SetWidth(256)
topRight:SetHeight(256)
topRight:SetPoint("TOPRIGHT", frame, "TOPRIGHT", 0, 0)

-- Cover the bank's bag-slot section with a neutral Blizzard panel and finish the
-- shortened account-bank window with a standard dialog border.
local lower = CreateFrame("Frame", nil, frame)
lower:SetPoint("TOPLEFT", frame, "TOPLEFT", 6, -248)
lower:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -6, 6)
lower:SetBackdrop({
    bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true,
    tileSize = 32,
    edgeSize = 18,
    insets = { left = 5, right = 5, top = 5, bottom = 5 }
})
lower:SetFrameLevel(frame:GetFrameLevel())

local portrait = frame:CreateTexture(nil, "ARTWORK")
portrait:SetWidth(60)
portrait:SetHeight(60)
portrait:SetPoint("TOPLEFT", frame, "TOPLEFT", 7, -6)
portrait:SetTexture("Interface\\Icons\\INV_Misc_Bag_07")
if SetPortraitToTexture then
    SetPortraitToTexture(portrait, "Interface\\Icons\\INV_Misc_Bag_07")
end

local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
title:SetPoint("TOP", frame, "TOP", 12, -18)
title:SetText("Baúl de Expediciones")

local subtitle = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
subtitle:SetPoint("TOPLEFT", frame, "TOPLEFT", 70, -44)
subtitle:SetText("Lo guardado aquí sobrevive a la muerte")

local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -42, -8)

local dropTarget = CreateFrame("Frame", nil, frame)
dropTarget:SetPoint("TOPLEFT", frame, "TOPLEFT", 34, -78)
dropTarget:SetWidth(308)
dropTarget:SetHeight(174)
dropTarget:EnableMouse(true)

local hint = lower:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
hint:SetPoint("CENTER", lower, "CENTER", 0, 0)
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

    ClearCursor()
    SendCommand("DEPOSIT|" .. entry)
    return true
end

dropTarget:SetScript("OnReceiveDrag", TryDepositCursorItem)
dropTarget:SetScript("OnMouseUp", function()
    if CursorHasItem() then TryDepositCursorItem() end
end)

local function CreateSlot(index)
    local name = "AdventurerGauntletStashSlot" .. index
    local button = CreateFrame("Button", name, frame, "ItemButtonTemplate")
    button:SetWidth(46)
    button:SetHeight(46)

    local column = (index - 1) % COLUMNS
    local row = math.floor((index - 1) / COLUMNS)
    button:SetPoint("TOPLEFT", frame, "TOPLEFT", 35 + column * 43, -78 - row * 43)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")

    -- The BankFrame texture already paints the slot border. Hide ItemButtonTemplate's
    -- own normal border so we only place the item icon on top of Blizzard's slot.
    local normal = button:GetNormalTexture()
    if normal then
        normal:SetTexture(nil)
        normal:Hide()
    end

    local highlight = button:GetHighlightTexture()
    if highlight then
        highlight:SetTexture("Interface\\Buttons\\ButtonHilight-Square")
        highlight:SetBlendMode("ADD")
        highlight:SetPoint("TOPLEFT", button, "TOPLEFT", 4, -4)
        highlight:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -4, 4)
    end

    button.icon = _G[name .. "IconTexture"]
    button.count = _G[name .. "Count"]
    if button.icon then
        button.icon:ClearAllPoints()
        button.icon:SetPoint("TOPLEFT", button, "TOPLEFT", 5, -5)
        button.icon:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -5, 5)
        button.icon:Hide()
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

    button:SetScript("OnReceiveDrag", TryDepositCursorItem)
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

local function GetTextureForItem(entry)
    local _, _, _, _, _, _, _, _, _, texture = GetItemInfo(entry)
    if texture then return texture end
    if GetItemIcon then return GetItemIcon(entry) end
    return "Interface\\Icons\\INV_Misc_QuestionMark"
end

local function PaintItem(button, item)
    button.entry = item and item.entry or nil

    if not item then
        if SetItemButtonTexture then
            SetItemButtonTexture(button, nil)
        elseif button.icon then
            button.icon:SetTexture(nil)
            button.icon:Hide()
        end
        if SetItemButtonCount then
            SetItemButtonCount(button, 0)
        elseif button.count then
            button.count:SetText("")
        end
        return
    end

    local texture = GetTextureForItem(item.entry)
    if SetItemButtonTexture then
        SetItemButtonTexture(button, texture)
    elseif button.icon then
        button.icon:SetTexture(texture)
        button.icon:Show()
    end

    if button.icon then
        button.icon:SetPoint("TOPLEFT", button, "TOPLEFT", 5, -5)
        button.icon:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -5, 5)
    end

    if SetItemButtonCount then
        SetItemButtonCount(button, item.count)
    elseif button.count then
        button.count:SetText(item.count > 1 and item.count or "")
    end

    if SetItemButtonQuality then
        local _, _, quality = GetItemInfo(item.entry)
        if quality then SetItemButtonQuality(button, quality, item.entry) end
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
