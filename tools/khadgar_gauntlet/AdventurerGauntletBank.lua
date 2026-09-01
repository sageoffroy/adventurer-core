-- Aventureros de Azeroth: account-wide expedition bank.
-- Reuses Blizzard's native 3.3.5 BankFrame and only replaces its data/actions
-- while the Expedition Bank is open.

local PREFIX = "AGBANK"
local BASE_SLOTS = 28
local BAG_SLOTS = 7
local MAX_BAG_CAPACITY = 36
local KHADGAR_ENTRY = 18166

local ITEMS = {}
local BAGS = {}
local PURCHASED_BAGS = 0
local NEXT_BAG_PRICE = 0
local BAG_FRAMES = {}
local PENDING_WITHDRAW = nil
local ACTIVE = false
local CLOSING_FROM_SERVER = false

local BANK = BankFrame
local PORTRAIT = BankPortraitTexture
local TITLE = BankFrameTitleText
local PURCHASE_INFO = BankFramePurchaseInfo
local PURCHASE_BUTTON = BankFramePurchaseButton
local COST_MONEY = BankFrameDetailMoneyFrame
local PLAYER_MONEY = BankFrameMoneyFrame
local CLOSE_BUTTON = BankCloseButton

local ORIGINAL = {
    bankOnShow = BANK:GetScript("OnShow"),
    bankOnHide = BANK:GetScript("OnHide"),
    bankOnEvent = BANK:GetScript("OnEvent"),
    closeOnClick = CLOSE_BUTTON:GetScript("OnClick"),
    purchaseOnClick = PURCHASE_BUTTON:GetScript("OnClick"),
    items = {},
    bags = {},
}

for index = 1, BASE_SLOTS do
    local button = _G["BankFrameItem" .. index]
    ORIGINAL.items[index] = {
        OnClick = button:GetScript("OnClick"),
        OnDragStart = button:GetScript("OnDragStart"),
        OnReceiveDrag = button:GetScript("OnReceiveDrag"),
        OnEnter = button:GetScript("OnEnter"),
        OnLeave = button:GetScript("OnLeave"),
    }
end

for index = 1, BAG_SLOTS do
    local button = _G["BankFrameBag" .. index]
    ORIGINAL.bags[index] = {
        OnClick = button:GetScript("OnClick"),
        OnDragStart = button:GetScript("OnDragStart"),
        OnReceiveDrag = button:GetScript("OnReceiveDrag"),
        OnEnter = button:GetScript("OnEnter"),
        OnLeave = button:GetScript("OnLeave"),
        UpdateTooltip = button.UpdateTooltip,
    }
end

local khadgarPortrait = CreateFrame("PlayerModel", "AdventurerGauntletBankKhadgarPortrait", BANK)
khadgarPortrait:SetWidth(60)
khadgarPortrait:SetHeight(60)
khadgarPortrait:SetPoint("TOPLEFT", BANK, "TOPLEFT", 7, -6)
khadgarPortrait:SetFrameLevel(BANK:GetFrameLevel() + 1)
khadgarPortrait:Hide()

local function PrepareKhadgarPortrait()
    PORTRAIT:Hide()
    khadgarPortrait:Show()
    khadgarPortrait:SetCreature(KHADGAR_ENTRY)
    if khadgarPortrait.SetPortraitZoom then
        khadgarPortrait:SetPortraitZoom(1)
    end
end

local function SendCommand(command)
    local player = UnitName("player")
    if player then
        SendAddonMessage(PREFIX, command, "WHISPER", player)
    end
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

local function UpdateTooltip(button)
    if not button.entry then
        GameTooltip:Hide()
        return
    end

    GameTooltip:SetOwner(button, "ANCHOR_RIGHT")
    GameTooltip:SetHyperlink("item:" .. button.entry)
    GameTooltip:Show()
end

local function RequestWithdraw(button)
    if not button or not button.entry or CursorHasItem() or PENDING_WITHDRAW then return end

    PENDING_WITHDRAW = {
        entry = button.entry,
        before = SnapshotInventoryEntry(button.entry),
    }
    SendCommand("WITHDRAW|" .. button.expeditionBankSlot)
end

local function DepositToSlot(bankSlot)
    local entry = CursorItemEntry()
    if not entry then return end

    ClearCursor()
    SendCommand("DEPOSIT|" .. entry .. "|" .. bankSlot)
end

local function ConfigureItemButton(button, bankSlot)
    button.expeditionBankSlot = bankSlot
    button.entry = nil
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")
    button:SetScript("OnEnter", UpdateTooltip)
    button:SetScript("OnLeave", function() GameTooltip:Hide() end)
    button:SetScript("OnClick", function(self)
        if CursorHasItem() then
            DepositToSlot(self.expeditionBankSlot)
        else
            RequestWithdraw(self)
        end
    end)
    button:SetScript("OnDragStart", RequestWithdraw)
    button:SetScript("OnReceiveDrag", function(self)
        DepositToSlot(self.expeditionBankSlot)
    end)
end

local function PaintItem(button, item)
    button.entry = item and item.entry or nil
    SetItemButtonTexture(button, item and (GetItemIcon(item.entry) or "Interface\\Icons\\INV_Misc_QuestionMark") or nil)
    SetItemButtonCount(button, item and item.count or 0)
    SetItemButtonDesaturated(button, false)
end

local function CreateBagFrame(bagIndex)
    local name = "AdventurerGauntletBankBag" .. bagIndex
    local bagFrame = CreateFrame("Frame", name, UIParent, "ContainerFrameTemplate")
    bagFrame:UnregisterAllEvents()
    bagFrame:SetScript("OnEvent", nil)
    -- ContainerFrameTemplate carries Blizzard's native OnShow handler, which
    -- calls ContainerFrame_Update() for a real bag ID. Expedition bags are
    -- virtual/account-wide and are painted below, so never run that handler.
    bagFrame:SetScript("OnShow", nil)
    bagFrame:SetFrameStrata("HIGH")
    bagFrame:SetPoint("TOPLEFT", BANK, "TOPRIGHT", 4 + ((bagIndex - 1) % 2) * 194, -(math.floor((bagIndex - 1) / 2) * 250))
    bagFrame:Hide()
    tinsert(UISpecialFrames, name)
    BAG_FRAMES[bagIndex] = bagFrame
    return bagFrame
end

local function LayoutVirtualBagBackground(bagFrame, size)
    local name = bagFrame:GetName()
    local top = _G[name .. "BackgroundTop"]
    local middle1 = _G[name .. "BackgroundMiddle1"]
    local middle2 = _G[name .. "BackgroundMiddle2"]
    local bottom = _G[name .. "BackgroundBottom"]
    local oneSlot = _G[name .. "Background1Slot"]
    local money = _G[name .. "MoneyFrame"]
    if not top or not middle1 or not middle2 or not bottom then return end

    local texture = "Interface\\ContainerFrame\\UI-Bag-Components-Bank"
    local columns = 4
    local rows = math.max(1, math.ceil(size / columns))
    local remainingRows = rows - 1
    local rowHeight = 41
    local textureHeight = 512
    local rowsPerMiddle = 6

    if oneSlot then oneSlot:Hide() end
    if money then money:Hide() end

    top:SetTexture(texture)
    top:Show()
    middle1:SetTexture(texture)
    middle2:SetTexture(texture)
    middle1:Hide()
    middle2:Hide()
    bottom:SetTexture(texture)

    if math.mod(size, columns) == 2 then
        top:SetTexCoord(0, 1, 0.189453125, 0.330078125)
        top:SetHeight(72)
    elseif rows == 1 then
        top:SetTexCoord(0, 1, 0.00390625, 0.16796875)
        top:SetHeight(86)
    else
        top:SetTexCoord(0, 1, 0.00390625, 0.18359375)
        top:SetHeight(94)
    end

    local middleHeight = 0
    local lastMiddle = middle1
    if rows == 1 then
        bottom:ClearAllPoints()
        bottom:SetPoint("TOP", middle1, "TOP", 0, 0)
        bottom:Show()
    else
        local firstRowPixelOffset = 9
        local firstRowTexCoordOffset = 0.353515625
        local middleCount = math.ceil(remainingRows / rowsPerMiddle)
        for index = 1, middleCount do
            local middle = _G[name .. "BackgroundMiddle" .. index]
            if middle then
                local height
                if remainingRows > rowsPerMiddle then
                    height = (rowsPerMiddle * rowHeight) + firstRowTexCoordOffset
                    remainingRows = remainingRows - rowsPerMiddle
                else
                    height = remainingRows * rowHeight - firstRowPixelOffset
                    remainingRows = 0
                end
                middle:SetHeight(height)
                middle:SetTexCoord(0, 1, firstRowTexCoordOffset, (height / textureHeight) + firstRowTexCoordOffset)
                middle:Show()
                middleHeight = middleHeight + height
                lastMiddle = middle
            end
        end
        bottom:ClearAllPoints()
        bottom:SetPoint("TOP", lastMiddle, "BOTTOM", 0, 0)
        bottom:Show()
    end

    bagFrame:SetWidth(192)
    bagFrame:SetHeight(top:GetHeight() + bottom:GetHeight() + middleHeight)
end

local function ConfigureBagContents(bagIndex)
    local bag = BAGS[bagIndex]
    if not bag then return end

    local bagFrame = BAG_FRAMES[bagIndex] or CreateBagFrame(bagIndex)
    LayoutVirtualBagBackground(bagFrame, bag.capacity)

    local nameText = _G[bagFrame:GetName() .. "Name"]
    if nameText then
        nameText:SetText(GetItemInfo(bag.entry) or "Bolsa")
    end

    local portrait = _G[bagFrame:GetName() .. "Portrait"]
    if portrait and SetPortraitToTexture then
        SetPortraitToTexture(portrait, GetItemIcon(bag.entry) or "Interface\\Icons\\INV_Misc_Bag_08")
    end

    for visual = 1, MAX_BAG_CAPACITY do
        local button = _G[bagFrame:GetName() .. "Item" .. visual]
        if button then
            if visual <= bag.capacity then
                local column = (visual - 1) % 4
                local row = math.floor((visual - 1) / 4)
                button:ClearAllPoints()
                button:SetPoint("TOPLEFT", bagFrame, "TOPLEFT", 17 + column * 39, -55 - row * 39)
                ConfigureItemButton(button, EncodeBagSlot(bagIndex, visual))
                PaintItem(button, ITEMS[EncodeBagSlot(bagIndex, visual)])
                button:Show()
            else
                button:Hide()
            end
        end
    end
end

local function UpdateBagTooltip(self)
    local bag = BAGS[self.expeditionBagIndex]
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    if bag then
        GameTooltip:SetHyperlink("item:" .. bag.entry)
    elseif self.expeditionBagIndex <= PURCHASED_BAGS then
        GameTooltip:SetText(BANK_BAG or "Casilla de bolsa")
    else
        GameTooltip:SetText(BANK_BAG_PURCHASE or "Comprar casilla de bolsa")
    end
    GameTooltip:Show()
end

local function ConfigureBagButton(button, bagIndex)
    button.expeditionBagIndex = bagIndex
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")

    -- GameTooltip periodically calls owner.UpdateTooltip while visible. Replace
    -- the native BankFrame implementation as well as OnEnter; otherwise it can
    -- call SetText(nil) for our virtual purchase slots after their state changes.
    button.UpdateTooltip = UpdateBagTooltip
    button:SetScript("OnEnter", UpdateBagTooltip)
    button:SetScript("OnLeave", function() GameTooltip:Hide() end)

    button:SetScript("OnReceiveDrag", function(self)
        if self.expeditionBagIndex > PURCHASED_BAGS or BAGS[self.expeditionBagIndex] then return end
        local entry = CursorItemEntry()
        if not entry then return end
        ClearCursor()
        SendCommand("INSTALLBAG|" .. self.expeditionBagIndex .. "|" .. entry)
    end)

    button:SetScript("OnDragStart", function(self)
        local bag = BAGS[self.expeditionBagIndex]
        if bag then
            SendCommand("REMOVEBAG|" .. self.expeditionBagIndex)
        end
    end)

    button:SetScript("OnClick", function(self, mouseButton)
        local bag = BAGS[self.expeditionBagIndex]
        if not bag then return end

        if mouseButton == "RightButton" and IsShiftKeyDown() then
            SendCommand("REMOVEBAG|" .. self.expeditionBagIndex)
            return
        end

        ConfigureBagContents(self.expeditionBagIndex)
        local bagFrame = BAG_FRAMES[self.expeditionBagIndex]
        if bagFrame:IsShown() then bagFrame:Hide() else bagFrame:Show() end
    end)
end

local function Refresh()
    for slot = 1, BASE_SLOTS do
        PaintItem(_G["BankFrameItem" .. slot], ITEMS[slot])
    end

    for index = 1, BAG_SLOTS do
        local button = _G["BankFrameBag" .. index]
        local bag = BAGS[index]
        local unlocked = index <= PURCHASED_BAGS
        local texture = _G[button:GetName() .. "IconTexture"]

        button:EnableMouse(true)
        if bag then
            SetItemButtonTexture(button, GetItemIcon(bag.entry) or "Interface\\Icons\\INV_Misc_Bag_08")
            SetItemButtonTextureVertexColor(button, 1, 1, 1)
        else
            local _, slotTexture = GetInventorySlotInfo("Bag" .. index)
            SetItemButtonTexture(button, slotTexture or "Interface\\PaperDoll\\UI-PaperDoll-Slot-Bag")
            if unlocked then
                SetItemButtonTextureVertexColor(button, 1, 1, 1)
            else
                SetItemButtonTextureVertexColor(button, 1, 0.1, 0.1)
            end
        end
        SetItemButtonCount(button, 0)
        if texture then texture:Show() end

        if BAG_FRAMES[index] and BAG_FRAMES[index]:IsShown() then
            ConfigureBagContents(index)
        end
    end

    MoneyFrame_Update("BankFrameDetailMoneyFrame", NEXT_BAG_PRICE)
    MoneyFrame_Update("BankFrameMoneyFrame", GetMoney())

    if SetMoneyFrameColor then
        SetMoneyFrameColor("BankFrameDetailMoneyFrame", GetMoney() >= NEXT_BAG_PRICE and "white" or "red")
    end

    if PURCHASED_BAGS < BAG_SLOTS and NEXT_BAG_PRICE > 0 then
        PURCHASE_INFO:Show()
    else
        PURCHASE_INFO:Hide()
    end
end

local function RestoreNativeBank()
    if not ACTIVE then return end

    ACTIVE = false
    khadgarPortrait:Hide()
    PORTRAIT:Show()

    BANK:SetScript("OnShow", ORIGINAL.bankOnShow)
    BANK:SetScript("OnHide", ORIGINAL.bankOnHide)
    BANK:SetScript("OnEvent", ORIGINAL.bankOnEvent)
    CLOSE_BUTTON:SetScript("OnClick", ORIGINAL.closeOnClick)
    PURCHASE_BUTTON:SetScript("OnClick", ORIGINAL.purchaseOnClick)

    for index = 1, BASE_SLOTS do
        local button = _G["BankFrameItem" .. index]
        local scripts = ORIGINAL.items[index]
        button:SetScript("OnClick", scripts.OnClick)
        button:SetScript("OnDragStart", scripts.OnDragStart)
        button:SetScript("OnReceiveDrag", scripts.OnReceiveDrag)
        button:SetScript("OnEnter", scripts.OnEnter)
        button:SetScript("OnLeave", scripts.OnLeave)
        button.expeditionBankSlot = nil
        button.entry = nil
    end

    for index = 1, BAG_SLOTS do
        local button = _G["BankFrameBag" .. index]
        local scripts = ORIGINAL.bags[index]
        button:SetScript("OnClick", scripts.OnClick)
        button:SetScript("OnDragStart", scripts.OnDragStart)
        button:SetScript("OnReceiveDrag", scripts.OnReceiveDrag)
        button:SetScript("OnEnter", scripts.OnEnter)
        button:SetScript("OnLeave", scripts.OnLeave)
        button.UpdateTooltip = scripts.UpdateTooltip
        button.expeditionBagIndex = nil
    end

    for _, bagFrame in pairs(BAG_FRAMES) do
        bagFrame:Hide()
    end

    PENDING_WITHDRAW = nil
end

local function CloseExpeditionBank(fromServer)
    if not ACTIVE then return end
    CLOSING_FROM_SERVER = fromServer and true or false
    HideUIPanel(BANK)
    CLOSING_FROM_SERVER = false
end

local function ActivateExpeditionBank()
    if ACTIVE then return end

    ACTIVE = true
    BANK:SetScript("OnShow", function()
        PlaySound("igMainMenuOpen")
    end)
    BANK:SetScript("OnHide", function()
        PlaySound("igMainMenuClose")
        if not CLOSING_FROM_SERVER then
            SendCommand("CLOSE")
        end
        RestoreNativeBank()
        if updateContainerFrameAnchors then updateContainerFrameAnchors() end
    end)
    BANK:SetScript("OnEvent", nil)

    CLOSE_BUTTON:SetScript("OnClick", function()
        CloseExpeditionBank(false)
    end)
    PURCHASE_BUTTON:SetScript("OnClick", function()
        PlaySound("igMainMenuOption")
        SendCommand("BUY")
    end)

    for index = 1, BASE_SLOTS do
        ConfigureItemButton(_G["BankFrameItem" .. index], index)
    end
    for index = 1, BAG_SLOTS do
        ConfigureBagButton(_G["BankFrameBag" .. index], index)
    end

    TITLE:SetText("Khadgar")
    PrepareKhadgarPortrait()
    ShowUIPanel(BANK)
end

local function HandleState(message)
    if message == "OPEN" then
        ITEMS = {}
        BAGS = {}
        ActivateExpeditionBank()
        return
    elseif message == "CLOSE" then
        CloseExpeditionBank(true)
        return
    elseif message == "DONE" then
        Refresh()
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
        BAGS[tonumber(bagIndex)] = {
            entry = tonumber(entry),
            capacity = tonumber(capacity),
        }
        return
    end

    local slot, itemEntry, count = string.match(message, "^ITEM|(%d+)|(%d+)|(%d+)$")
    if slot then
        ITEMS[tonumber(slot)] = {
            entry = tonumber(itemEntry),
            count = tonumber(count),
        }
    end
end

local function SystemMessageFilter(self, event, message, ...)
    if type(message) ~= "string" or string.sub(message, 1, 7) ~= "AGBANK|" then
        return false, message, ...
    end
    HandleState(string.sub(message, 8))
    return true
end
ChatFrame_AddMessageEventFilter("CHAT_MSG_SYSTEM", SystemMessageFilter)

local events = CreateFrame("Frame")
events:RegisterEvent("CHAT_MSG_ADDON")
events:RegisterEvent("BAG_UPDATE")
events:RegisterEvent("PLAYER_MONEY")
events:SetScript("OnEvent", function(self, event, ...)
    if event == "CHAT_MSG_ADDON" then
        local prefix, message = ...
        if prefix == PREFIX then HandleState(message) end
    elseif event == "BAG_UPDATE" then
        TryPickupPendingWithdraw()
    elseif event == "PLAYER_MONEY" and ACTIVE then
        MoneyFrame_Update("BankFrameMoneyFrame", GetMoney())
    end
end)
