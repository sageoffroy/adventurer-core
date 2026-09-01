-- Aventureros de Azeroth: account-wide expedition bank.
-- Mirrors Blizzard's 3.3.5 BankFrame layout and interaction model.

local PREFIX = "AGBANK"
local FRAME_NAME = "AdventurerGauntletBankFrame"
local BASE_SLOTS = 28
local BAG_SLOTS = 7
local MAX_BAG_CAPACITY = 36
local COLUMNS = 7

local ITEMS = {}
local BAGS = {}
local PURCHASED_BAGS = 0
local NEXT_BAG_PRICE = 0
local MAIN_SLOTS = {}
local BAG_BUTTONS = {}
local BAG_FRAMES = {}
local PENDING_WITHDRAW = nil

local function SendCommand(command)
    local player = UnitName("player")
    if player then SendAddonMessage(PREFIX, command, "WHISPER", player) end
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
                    return
                end
            end
        end
    end
end

local function EncodeBagSlot(bagIndex, innerSlot)
    return BASE_SLOTS + ((bagIndex - 1) * MAX_BAG_CAPACITY) + innerSlot
end

local frame = CreateFrame("Frame", FRAME_NAME, UIParent)
frame:SetWidth(384)
frame:SetHeight(512)
frame:SetFrameStrata("HIGH")
frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 0, -104)
frame:EnableMouse(true)
frame:Hide()
UIPanelWindows[FRAME_NAME] = { area = "left", pushable = 5, whileDead = 1 }
tinsert(UISpecialFrames, FRAME_NAME)

local function AddBankTexture(path, width, height, point, relativePoint)
    local texture = frame:CreateTexture(nil, "ARTWORK")
    texture:SetTexture(path)
    texture:SetWidth(width)
    texture:SetHeight(height)
    texture:SetPoint(point, frame, relativePoint)
end

AddBankTexture("Interface\\BankFrame\\UI-BankFrame-TopLeft", 256, 256, "TOPLEFT", "TOPLEFT")
AddBankTexture("Interface\\BankFrame\\UI-BankFrame-TopRight", 128, 256, "TOPRIGHT", "TOPRIGHT")
AddBankTexture("Interface\\BankFrame\\UI-BankFrame-BotLeft", 256, 256, "BOTTOMLEFT", "BOTTOMLEFT")
AddBankTexture("Interface\\BankFrame\\UI-BankFrame-BotRight", 128, 256, "BOTTOMRIGHT", "BOTTOMRIGHT")

local portrait = frame:CreateTexture(nil, "OVERLAY")
portrait:SetWidth(58)
portrait:SetHeight(58)
portrait:SetPoint("TOPLEFT", frame, "TOPLEFT", 12, -8)
portrait:SetTexture("Interface\\Icons\\INV_Box_04")
if SetPortraitToTexture then SetPortraitToTexture(portrait, "Interface\\Icons\\INV_Box_04") end

local title = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
title:SetPoint("CENTER", frame, "CENTER", 6, 230)
title:SetText("Banco de Expediciones")

local itemLabel = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
itemLabel:SetPoint("CENTER", frame, "CENTER", -11, 195)
itemLabel:SetText("Casillas de objeto")

local bagLabel = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
bagLabel:SetPoint("CENTER", frame, "CENTER", -11, -5)
bagLabel:SetText("Casillas de bolsa")

local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
close:SetPoint("CENTER", frame, "TOPRIGHT", -44, -26)
close:SetScript("OnClick", function() HideUIPanel(frame) end)

local buyText = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
buyText:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 42, 83)
buyText:SetText("¿Quieres comprar espacio para una bolsa adicional?")

local costLabel = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
costLabel:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 42, 47)
costLabel:SetText("Coste:")

local costMoney = CreateFrame("Frame", FRAME_NAME .. "CostMoney", frame, "SmallMoneyFrameTemplate")
costMoney:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 95, 40)

local money = CreateFrame("Frame", FRAME_NAME .. "Money", frame, "SmallMoneyFrameTemplate")
money:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -30, 9)

local buy = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
buy:SetWidth(110)
buy:SetHeight(24)
buy:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -43, 37)
buy:SetText("Comprar")
buy:SetScript("OnClick", function() SendCommand("BUY") end)

local function UpdateTooltip(button)
    if not button.entry then GameTooltip:Hide(); return end
    GameTooltip:SetOwner(button, "ANCHOR_RIGHT")
    GameTooltip:SetHyperlink("item:" .. button.entry)
    GameTooltip:Show()
end

local function RequestWithdraw(button)
    if not button or not button.entry or CursorHasItem() or PENDING_WITHDRAW then return end
    PENDING_WITHDRAW = { entry = button.entry, before = SnapshotInventoryEntry(button.entry) }
    SendCommand("WITHDRAW|" .. button.bankSlot)
end

local function DepositToSlot(bankSlot)
    local entry = CursorItemEntry()
    if not entry then return end
    ClearCursor()
    SendCommand("DEPOSIT|" .. entry .. "|" .. bankSlot)
end

local function ConfigureItemButton(button, bankSlot)
    button.bankSlot = bankSlot
    button.entry = nil
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")
    button:SetScript("OnEnter", UpdateTooltip)
    button:SetScript("OnLeave", function() GameTooltip:Hide() end)
    button:SetScript("OnClick", function(self)
        if CursorHasItem() then DepositToSlot(self.bankSlot) else RequestWithdraw(self) end
    end)
    button:SetScript("OnDragStart", RequestWithdraw)
    button:SetScript("OnReceiveDrag", function(self) DepositToSlot(self.bankSlot) end)
end

for index = 1, BASE_SLOTS do
    local name = FRAME_NAME .. "Item" .. index
    local button = CreateFrame("Button", name, frame, "ItemButtonTemplate")
    button:SetWidth(37)
    button:SetHeight(37)
    local column = (index - 1) % COLUMNS
    local row = math.floor((index - 1) / COLUMNS)
    button:SetPoint("TOPLEFT", frame, "TOPLEFT", 40 + column * 43, -73 - row * 44)
    ConfigureItemButton(button, index)
    MAIN_SLOTS[index] = button
end

local function CreateBagFrame(bagIndex)
    local bagFrame = CreateFrame("Frame", FRAME_NAME .. "Bag" .. bagIndex, UIParent, "ContainerFrameTemplate")
    bagFrame:UnregisterAllEvents()
    bagFrame:SetScript("OnEvent", nil)
    bagFrame:SetWidth(192)
    bagFrame:SetPoint("TOPLEFT", frame, "TOPRIGHT", 4 + ((bagIndex - 1) % 2) * 194, -(math.floor((bagIndex - 1) / 2) * 250))
    bagFrame:SetFrameStrata("HIGH")
    bagFrame:Hide()
    tinsert(UISpecialFrames, bagFrame:GetName())
    BAG_FRAMES[bagIndex] = bagFrame
    return bagFrame
end

local function ConfigureBagContents(bagIndex)
    local bag = BAGS[bagIndex]
    local bagFrame = BAG_FRAMES[bagIndex] or CreateBagFrame(bagIndex)
    local capacity = bag and bag.capacity or 0
    local rows = math.max(1, math.ceil(capacity / 4))
    bagFrame:SetHeight(74 + rows * 39)

    local nameText = _G[bagFrame:GetName() .. "Name"]
    if nameText then nameText:SetText(bag and (GetItemInfo(bag.entry) or "Bolsa") or "Bolsa") end
    local portraitTexture = _G[bagFrame:GetName() .. "Portrait"]
    if portraitTexture and bag and SetPortraitToTexture then
        SetPortraitToTexture(portraitTexture, GetItemIcon(bag.entry) or "Interface\\Icons\\INV_Misc_Bag_08")
    end

    for visual = 1, MAX_BAG_CAPACITY do
        local button = _G[bagFrame:GetName() .. "Item" .. visual]
        if button then
            if visual <= capacity then
                local col = (visual - 1) % 4
                local row = math.floor((visual - 1) / 4)
                button:ClearAllPoints()
                button:SetPoint("TOPLEFT", bagFrame, "TOPLEFT", 17 + col * 39, -55 - row * 39)
                ConfigureItemButton(button, EncodeBagSlot(bagIndex, visual))
                button:Show()
            else
                button:Hide()
            end
        end
    end
end

for index = 1, BAG_SLOTS do
    local name = FRAME_NAME .. "BagSlot" .. index
    local button = CreateFrame("Button", name, frame, "ItemButtonTemplate")
    button:SetWidth(37)
    button:SetHeight(37)
    button:SetPoint("TOPLEFT", frame, "TOPLEFT", 40 + (index - 1) * 43, -292)
    button.bagIndex = index
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")
    button:SetScript("OnReceiveDrag", function(self)
        if self.bagIndex > PURCHASED_BAGS then return end
        local entry = CursorItemEntry()
        if not entry then return end
        ClearCursor()
        SendCommand("INSTALLBAG|" .. self.bagIndex .. "|" .. entry)
    end)
    button:SetScript("OnClick", function(self, mouseButton)
        local bag = BAGS[self.bagIndex]
        if not bag then return end
        if mouseButton == "RightButton" and IsShiftKeyDown() then
            SendCommand("REMOVEBAG|" .. self.bagIndex)
            return
        end
        ConfigureBagContents(self.bagIndex)
        local bagFrame = BAG_FRAMES[self.bagIndex]
        if bagFrame:IsShown() then bagFrame:Hide() else bagFrame:Show() end
    end)
    BAG_BUTTONS[index] = button
end

local function PaintItem(button, item)
    button.entry = item and item.entry or nil
    SetItemButtonTexture(button, item and (GetItemIcon(item.entry) or "Interface\\Icons\\INV_Misc_QuestionMark") or nil)
    SetItemButtonCount(button, item and item.count or 0)
end

local function Refresh()
    for slot = 1, BASE_SLOTS do PaintItem(MAIN_SLOTS[slot], ITEMS[slot]) end

    for index = 1, BAG_SLOTS do
        local button = BAG_BUTTONS[index]
        local bag = BAGS[index]
        local unlocked = index <= PURCHASED_BAGS
        button:EnableMouse(unlocked)
        if bag then
            SetItemButtonTexture(button, GetItemIcon(bag.entry) or "Interface\\Icons\\INV_Misc_Bag_08")
            button:SetAlpha(1)
        else
            SetItemButtonTexture(button, "Interface\\PaperDoll\\UI-PaperDoll-Slot-Bag")
            button:SetAlpha(unlocked and 1 or 0.45)
        end
        if BAG_FRAMES[index] and BAG_FRAMES[index]:IsShown() then ConfigureBagContents(index) end
    end

    for bagIndex, bag in pairs(BAGS) do
        local bagFrame = BAG_FRAMES[bagIndex]
        if bagFrame then
            for inner = 1, bag.capacity do
                local button = _G[bagFrame:GetName() .. "Item" .. inner]
                if button then PaintItem(button, ITEMS[EncodeBagSlot(bagIndex, inner)]) end
            end
        end
    end

    if MoneyFrame_Update then
        MoneyFrame_Update(costMoney:GetName(), NEXT_BAG_PRICE)
        MoneyFrame_Update(money:GetName(), GetMoney())
    end

    local canBuy = PURCHASED_BAGS < BAG_SLOTS and NEXT_BAG_PRICE > 0
    if canBuy then
        buy:Show(); buyText:Show(); costLabel:Show(); costMoney:Show()
    else
        buy:Hide(); buyText:Hide(); costLabel:Hide(); costMoney:Hide()
    end
end

local function CloseAll()
    HideUIPanel(frame)
    for _, bagFrame in pairs(BAG_FRAMES) do bagFrame:Hide() end
    PENDING_WITHDRAW = nil
end

local function HandleState(message)
    if message == "OPEN" then
        ITEMS = {}; BAGS = {}
        ShowUIPanel(frame)
        return
    elseif message == "CLOSE" then
        CloseAll()
        return
    elseif message == "DONE" then
        Refresh(); ShowUIPanel(frame)
        return
    end

    local purchased, price = string.match(message, "^META|(%d+)|(%d+)$")
    if purchased then
        PURCHASED_BAGS = tonumber(purchased)
        NEXT_BAG_PRICE = tonumber(price)
        return
    end

    local bagIndex, entry, capacity = string.match(message, "^BAG|(%d+)|(%d+)|(%d+)$")
    if bagIndex then
        BAGS[tonumber(bagIndex)] = { entry = tonumber(entry), capacity = tonumber(capacity) }
        return
    end

    local slot, itemEntry, count = string.match(message, "^ITEM|(%d+)|(%d+)|(%d+)$")
    if slot then ITEMS[tonumber(slot)] = { entry = tonumber(itemEntry), count = tonumber(count) } end
end

local function SystemMessageFilter(self, event, message, ...)
    if type(message) ~= "string" or string.sub(message, 1, 7) ~= "AGBANK|" then return false, message, ... end
    HandleState(string.sub(message, 8))
    return true
end
ChatFrame_AddMessageEventFilter("CHAT_MSG_SYSTEM", SystemMessageFilter)

local events = CreateFrame("Frame")
events:RegisterEvent("CHAT_MSG_ADDON")
events:RegisterEvent("BAG_UPDATE")
events:SetScript("OnEvent", function(self, event, ...)
    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if prefix == PREFIX then HandleState(message) end
    elseif event == "BAG_UPDATE" then
        TryPickupPendingWithdraw()
        if frame:IsShown() and MoneyFrame_Update then MoneyFrame_Update(money:GetName(), GetMoney()) end
    end
end)
