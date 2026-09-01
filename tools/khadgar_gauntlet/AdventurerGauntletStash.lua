-- Adventurer Gauntlet account stash UI for WoW 3.3.5a.
-- Uses Blizzard's native BankFrame artwork while keeping account-level stash logic.

local STASH_ITEMS = {}
local SLOTS = {}
local MAX_SLOTS = 28
local COLUMNS = 7
local PREFIX = "AGSTASH"
local FRAME_NAME = "AdventurerGauntletStashFrame"
local PENDING_WITHDRAW = nil

local function SendCommand(command)
    local player = UnitName("player")
    if not player then return end
    SendAddonMessage(PREFIX, command, "WHISPER", player)
end

local function ItemIdFromLink(link)
    if not link then return nil end
    local id = string.match(link, "item:(%d+)")
    return id and tonumber(id) or nil
end

local function CursorItemEntry()
    local cursorType, itemID = GetCursorInfo()
    if cursorType == "item" then return tonumber(itemID) end
    return nil
end

local function SnapshotInventoryEntry(entry)
    local snapshot = {}
    for bag = 0, NUM_BAG_SLOTS do
        for slot = 1, GetContainerNumSlots(bag) do
            local id = ItemIdFromLink(GetContainerItemLink(bag, slot))
            if id == entry then
                local _, count = GetContainerItemInfo(bag, slot)
                snapshot[bag .. ":" .. slot] = count or 1
            end
        end
    end
    return snapshot
end

local function TryPickupPendingWithdraw()
    local pending = PENDING_WITHDRAW
    if not pending or CursorHasItem() then return end

    for bag = 0, NUM_BAG_SLOTS do
        for slot = 1, GetContainerNumSlots(bag) do
            local id = ItemIdFromLink(GetContainerItemLink(bag, slot))
            if id == pending.entry then
                local _, count = GetContainerItemInfo(bag, slot)
                local before = pending.before[bag .. ":" .. slot] or 0
                if (count or 1) > before then
                    PENDING_WITHDRAW = nil
                    PickupContainerItem(bag, slot)
                    if not CursorHasItem() then PENDING_WITHDRAW = pending end
                    return
                end
            end
        end
    end
end

local function FirstFreeStashSlot()
    for slot = 1, MAX_SLOTS do
        if not STASH_ITEMS[slot] then return slot end
    end
    return nil
end

local function TryDepositCursorItem(targetSlot)
    local entry = CursorItemEntry()
    if not entry then return false end

    targetSlot = targetSlot or FirstFreeStashSlot()
    if not targetSlot then
        UIErrorsFrame:AddMessage("El Baúl de Expediciones está lleno.", 1.0, 0.1, 0.1, 1.0)
        return false
    end
    if STASH_ITEMS[targetSlot] then
        UIErrorsFrame:AddMessage("Esa casilla ya está ocupada.", 1.0, 0.1, 0.1, 1.0)
        return false
    end

    ClearCursor()
    SendCommand("DEPOSIT|" .. entry .. "|" .. targetSlot)
    return true
end

local function RequestWithdraw(button)
    if not button or not button.entry or PENDING_WITHDRAW or CursorHasItem() then return end

    PENDING_WITHDRAW = {
        slot = button.stashSlot,
        entry = button.entry,
        before = SnapshotInventoryEntry(button.entry),
    }
    SendCommand("WITHDRAW|" .. button.stashSlot)
end

local frame = CreateFrame("Frame", FRAME_NAME, UIParent)
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
frame:SetScript("OnShow", function() PlaySound("igMainMenuOpen") end)
frame:SetScript("OnHide", function()
    GameTooltip:Hide()
    PENDING_WITHDRAW = nil
    PlaySound("igMainMenuClose")
end)
frame:Hide()
tinsert(UISpecialFrames, FRAME_NAME)

-- Exact Blizzard bank artwork used by the working Doan-safe version.
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
close:SetScript("OnClick", function() frame:Hide() end)

local dropTarget = CreateFrame("Frame", nil, frame)
dropTarget:SetPoint("TOPLEFT", frame, "TOPLEFT", 34, -78)
dropTarget:SetWidth(308)
dropTarget:SetHeight(174)
dropTarget:EnableMouse(true)
dropTarget:SetScript("OnReceiveDrag", function() TryDepositCursorItem(nil) end)
dropTarget:SetScript("OnMouseUp", function()
    if CursorHasItem() then TryDepositCursorItem(nil) end
end)

local hint = lower:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
hint:SetPoint("CENTER", lower, "CENTER", 0, 0)
hint:SetText("Arrastra equipo para guardar · Clic para retirar")

local function UpdateStashTooltip(button)
    if not button or not button.entry then
        GameTooltip:Hide()
        return
    end
    GameTooltip:SetOwner(button, "ANCHOR_RIGHT")
    GameTooltip:SetHyperlink("item:" .. button.entry)
    GameTooltip:Show()
end

local function CreateSlot(index)
    local name = "AdventurerGauntletStashSlot" .. index
    local button = CreateFrame("Button", name, frame, "ItemButtonTemplate")
    button:SetWidth(46)
    button:SetHeight(46)

    local column = (index - 1) % COLUMNS
    local row = math.floor((index - 1) / COLUMNS)
    button:SetPoint("TOPLEFT", frame, "TOPLEFT", 35 + column * 43, -78 - row * 43)
    button.stashSlot = index
    button:SetID(index)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")

    local normal = button:GetNormalTexture()
    if normal then
        normal:SetTexture(nil)
        normal:Hide()
    end

    local highlight = button:GetHighlightTexture()
    if highlight then
        highlight:SetTexture("Interface\\Buttons\\ButtonHilight-Square")
        highlight:SetBlendMode("ADD")
        highlight:ClearAllPoints()
        highlight:SetPoint("TOPLEFT", button, "TOPLEFT", 4, -4)
        highlight:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -4, 4)
    end

    local icon = _G[name .. "IconTexture"]
    if icon then
        icon:ClearAllPoints()
        icon:SetPoint("TOPLEFT", button, "TOPLEFT", 5, -5)
        icon:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -5, 5)
    end

    button.entry = nil
    button.UpdateTooltip = UpdateStashTooltip
    button:SetScript("OnEnter", function(self) self:UpdateTooltip() end)
    button:SetScript("OnLeave", function() GameTooltip:Hide() end)
    button:SetScript("OnClick", function(self)
        if CursorHasItem() then
            TryDepositCursorItem(self.stashSlot)
            return
        end
        RequestWithdraw(self)
    end)
    button:SetScript("OnDragStart", function(self) RequestWithdraw(self) end)
    button:SetScript("OnReceiveDrag", function(self) TryDepositCursorItem(self.stashSlot) end)
    return button
end

for index = 1, MAX_SLOTS do
    SLOTS[index] = CreateSlot(index)
end

local function PaintItem(button, item)
    button.entry = item and item.entry or nil

    if not item then
        SetItemButtonTexture(button, nil)
        SetItemButtonCount(button, 0)
        SetItemButtonDesaturated(button, false)
        if GameTooltip:GetOwner() == button then GameTooltip:Hide() end
        return
    end

    local texture = GetItemIcon(item.entry) or "Interface\\Icons\\INV_Misc_QuestionMark"
    SetItemButtonTexture(button, texture)
    SetItemButtonCount(button, item.count)
    SetItemButtonDesaturated(button, false)
    if SetItemButtonQuality then
        local _, _, quality = GetItemInfo(item.entry)
        if quality then SetItemButtonQuality(button, quality, item.entry) end
    end
    if GameTooltip:GetOwner() == button then button:UpdateTooltip() end
end

local function RefreshUI()
    for slot = 1, MAX_SLOTS do
        PaintItem(SLOTS[slot], STASH_ITEMS[slot])
    end
end

local function HandleState(message)
    if message == "OPEN" then
        STASH_ITEMS = {}
        frame:Show()
        return
    end

    if message == "CLOSE" then
        frame:Hide()
        STASH_ITEMS = {}
        return
    end

    if message == "DONE" then
        RefreshUI()
        frame:Show()
        if PENDING_WITHDRAW and STASH_ITEMS[PENDING_WITHDRAW.slot] then
            PENDING_WITHDRAW = nil
        end
        return
    end

    local slot, entry, count = string.match(message, "^S|(%d+)|(%d+)|(%d+)$")
    if slot and entry and count then
        slot = tonumber(slot)
        if slot and slot >= 1 and slot <= MAX_SLOTS then
            STASH_ITEMS[slot] = { entry = tonumber(entry), count = tonumber(count) }
        end
    end
end

local function SystemMessageFilter(self, event, message, ...)
    if type(message) ~= "string" or string.sub(message, 1, 8) ~= "AGSTASH|" then
        return false, message, ...
    end
    HandleState(string.sub(message, 9))
    return true
end
ChatFrame_AddMessageEventFilter("CHAT_MSG_SYSTEM", SystemMessageFilter)

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("CHAT_MSG_ADDON")
eventFrame:RegisterEvent("BAG_UPDATE")
eventFrame:RegisterEvent("GET_ITEM_INFO_RECEIVED")
eventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if prefix == PREFIX then HandleState(message) end
    elseif event == "BAG_UPDATE" then
        TryPickupPendingWithdraw()
    elseif event == "GET_ITEM_INFO_RECEIVED" and frame:IsShown() then
        RefreshUI()
    end
end)
