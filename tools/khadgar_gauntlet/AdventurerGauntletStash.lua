-- Adventurer Gauntlet account stash UI for WoW 3.3.5a.
local STASH_ITEMS = {}
local SLOTS = {}
local MAX_SLOTS = 16
local PREFIX = "AGSTASH"
local COMMAND_PREFIX = "AGSTASH|"
local FRAME_NAME = "AdventurerGauntletStashFrame"
local PENDING_WITHDRAW = nil

local function SendCommand(command)
    local target = UnitName("player")
    if not target or target == "" then return end
    -- Use the same self-whisper transport already proven by SpellDraft on the
    -- 3.3.5a client. The server filters these protocol messages before chat.
    SendChatMessage(COMMAND_PREFIX .. command, "WHISPER", nil, target)
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

local frame = CreateFrame("Frame", FRAME_NAME, UIParent, "ContainerFrameTemplate")
frame:UnregisterAllEvents()
frame:SetScript("OnEvent", nil)
frame:SetScript("OnShow", function() PlaySound("igBackPackOpen") end)
frame:SetScript("OnHide", function() GameTooltip:Hide(); PlaySound("igBackPackClose") end)
frame:SetScript("OnReceiveDrag", function() TryDepositCursorItem(nil) end)
frame:SetID(100)
frame.size = MAX_SLOTS
frame:SetWidth(192)
frame:SetHeight(240)
frame:ClearAllPoints()
frame:SetPoint("BOTTOMRIGHT", UIParent, "BOTTOMRIGHT", -18, 92)
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", function(self) if not CursorHasItem() then self:StartMoving() end end)
frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
frame:Hide()
tinsert(UISpecialFrames, FRAME_NAME)

local bgTop = _G[FRAME_NAME .. "BackgroundTop"]
local bgMiddle1 = _G[FRAME_NAME .. "BackgroundMiddle1"]
local bgMiddle2 = _G[FRAME_NAME .. "BackgroundMiddle2"]
local bgBottom = _G[FRAME_NAME .. "BackgroundBottom"]
local bgOneSlot = _G[FRAME_NAME .. "Background1Slot"]
local moneyFrame = _G[FRAME_NAME .. "MoneyFrame"]
local nameText = _G[FRAME_NAME .. "Name"]
local portrait = _G[FRAME_NAME .. "Portrait"]
local portraitButton = _G[FRAME_NAME .. "PortraitButton"]
local closeButton = _G[FRAME_NAME .. "CloseButton"]

if bgOneSlot then bgOneSlot:Hide() end
if bgTop then
    bgTop:SetTexture("Interface\\ContainerFrame\\UI-BackpackBackground")
    bgTop:SetHeight(256)
    bgTop:SetTexCoord(0, 1, 0, 1)
    bgTop:Show()
end
if bgMiddle1 then bgMiddle1:Hide() end
if bgMiddle2 then bgMiddle2:Hide() end
if bgBottom then bgBottom:Hide() end
if moneyFrame then moneyFrame:Show() end
if nameText then nameText:SetText("Baúl de Expediciones") end
if portrait then
    portrait:SetTexture("Interface\\Icons\\INV_Box_04")
    if SetPortraitToTexture then SetPortraitToTexture(portrait, "Interface\\Icons\\INV_Box_04") end
end
if portraitButton then
    portraitButton:SetID(100)
    portraitButton:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:SetText("Baúl de Expediciones", 1.0, 1.0, 1.0)
        GameTooltip:AddLine("Lo guardado aquí sobrevive a la muerte.", nil, nil, nil, true)
        GameTooltip:Show()
    end)
    portraitButton:SetScript("OnLeave", function() GameTooltip:Hide() end)
end
if closeButton then closeButton:SetScript("OnClick", function() frame:Hide() end) end

local function UpdateStashTooltip(button)
    if not button or not button.entry then GameTooltip:Hide(); return end
    GameTooltip:SetOwner(button, "ANCHOR_LEFT")
    GameTooltip:SetHyperlink("item:" .. button.entry)
    GameTooltip:Show()
end

local function ConfigureSlot(button, visualIndex, stashSlot)
    -- Stable 4x4 backpack-style grid: slots 1..16 read left-to-right and
    -- top-to-bottom. Do not reverse the logical slot IDs against the visual UI.
    local column = (visualIndex - 1) % 4
    local row = math.floor((visualIndex - 1) / 4)
    button:ClearAllPoints()
    button:SetPoint("TOPLEFT", frame, "TOPLEFT", 14 + column * 39, -72 - row * 39)
    button.stashSlot = stashSlot
    button:Show()
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")
    button:SetScript("OnClick", function(self)
        if CursorHasItem() then TryDepositCursorItem(self.stashSlot); return end
        RequestWithdraw(self)
    end)
    button:SetScript("OnDragStart", function(self) RequestWithdraw(self) end)
    button:SetScript("OnReceiveDrag", function(self) TryDepositCursorItem(self.stashSlot) end)
    button.UpdateTooltip = UpdateStashTooltip
    button:SetScript("OnEnter", function(self) self:UpdateTooltip() end)
    button:SetScript("OnLeave", function() GameTooltip:Hide() end)
    local questTexture = _G[button:GetName() .. "IconQuestTexture"]
    if questTexture then questTexture:Hide() end
    local cooldown = _G[button:GetName() .. "Cooldown"]
    if cooldown then cooldown:Hide() end
end

for visualIndex = 1, MAX_SLOTS do
    local button = _G[FRAME_NAME .. "Item" .. visualIndex]
    local stashSlot = visualIndex
    button:SetID(stashSlot)
    ConfigureSlot(button, visualIndex, stashSlot)
    SLOTS[stashSlot] = button
end
for visualIndex = MAX_SLOTS + 1, 36 do
    local button = _G[FRAME_NAME .. "Item" .. visualIndex]
    if button then button:Hide() end
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
    if GameTooltip:GetOwner() == button then button:UpdateTooltip() end
end

local function RefreshUI()
    for slot = 1, MAX_SLOTS do PaintItem(SLOTS[slot], STASH_ITEMS[slot]) end
end

local function HandleState(message)
    if message == "OPEN" then STASH_ITEMS = {}; frame:Show(); return end
    if message == "DONE" then
        RefreshUI(); frame:Show()
        if PENDING_WITHDRAW and STASH_ITEMS[PENDING_WITHDRAW.slot] then PENDING_WITHDRAW = nil end
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

local function StashWhisperFilter(_, _, message, sender)
    if sender == UnitName("player") and type(message) == "string" and string.sub(message, 1, string.len(COMMAND_PREFIX)) == COMMAND_PREFIX then
        return true
    end
    return false
end
ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER", StashWhisperFilter)
ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER_INFORM", StashWhisperFilter)

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("BAG_UPDATE")
eventFrame:SetScript("OnEvent", function(self, event)
    if event == "BAG_UPDATE" then
        TryPickupPendingWithdraw()
    end
end)
