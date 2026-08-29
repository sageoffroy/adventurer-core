-- Adventurer Gauntlet account stash UI for WoW 3.3.5a.
-- Uses Blizzard's real ContainerFrame backpack template. Only the data source and
-- slot interactions are custom; the frame, background and slot art are stock WoW.

local STASH_ITEMS = {}
local SLOTS = {}
local MAX_SLOTS = 16
local PREFIX = "AGSTASH"
local FRAME_NAME = "AdventurerGauntletStashFrame"

local function SendCommand(command)
    if not UnitName("player") then return end
    SendAddonMessage(PREFIX, command, "WHISPER", UnitName("player"))
end

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

-- ContainerFrameTemplate is the exact template used by the 3.3.5 backpack/bags.
local frame = CreateFrame("Frame", FRAME_NAME, UIParent, "ContainerFrameTemplate")

-- Its inherited OnLoad registers real BAG_* events. This frame is account-backed,
-- so detach it from the native bag system immediately and keep only its visuals.
frame:UnregisterAllEvents()
frame:SetScript("OnEvent", nil)
frame:SetScript("OnShow", function()
    PlaySound("igBackPackOpen")
end)
frame:SetScript("OnHide", function()
    GameTooltip:Hide()
    PlaySound("igBackPackClose")
end)
frame:SetScript("OnReceiveDrag", TryDepositCursorItem)
frame:SetID(100)
frame.size = MAX_SLOTS
frame:SetWidth(192)
frame:SetHeight(240)
frame:ClearAllPoints()
frame:SetPoint("BOTTOMRIGHT", UIParent, "BOTTOMRIGHT", -18, 92)
frame:SetMovable(true)
frame:EnableMouse(true)
frame:RegisterForDrag("LeftButton")
frame:SetScript("OnDragStart", function(self)
    if not CursorHasItem() then self:StartMoving() end
end)
frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
frame:Hide()

tinsert(UISpecialFrames, FRAME_NAME)

-- Configure the inherited ContainerFrame exactly as Blizzard configures bag 0
-- (the backpack) in ContainerFrame_GenerateFrame.
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
if portrait then SetBagPortraitTexture(portrait, 0) end

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

if closeButton then
    closeButton:SetScript("OnClick", function() frame:Hide() end)
end

local function ConfigureSlot(button, visualIndex)
    button:ClearAllPoints()

    -- These are Blizzard's exact backpack anchors from ContainerFrame_GenerateFrame.
    if visualIndex == 1 then
        button:SetPoint("BOTTOMRIGHT", frame, "TOPRIGHT", -12, -208)
    elseif ((visualIndex - 1) % 4) == 0 then
        button:SetPoint("BOTTOMRIGHT", _G[FRAME_NAME .. "Item" .. (visualIndex - 4)], "TOPRIGHT", 0, 4)
    else
        button:SetPoint("BOTTOMRIGHT", _G[FRAME_NAME .. "Item" .. (visualIndex - 1)], "BOTTOMLEFT", -5, 0)
    end

    button:Show()
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")

    -- Replace the stock bag API handlers while keeping the stock button visuals.
    button:SetScript("OnClick", function(self)
        if CursorHasItem() then
            TryDepositCursorItem()
            return
        end
        if self.entry then
            SendCommand("WITHDRAW|" .. self.entry)
        end
    end)
    button:SetScript("OnDragStart", function(self)
        if self.entry then
            SendCommand("WITHDRAW|" .. self.entry)
        end
    end)
    button:SetScript("OnReceiveDrag", TryDepositCursorItem)
    button:SetScript("OnEnter", function(self)
        if not self.entry then return end
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:SetHyperlink("item:" .. self.entry)
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function()
        GameTooltip:Hide()
        ResetCursor()
    end)

    local questTexture = _G[button:GetName() .. "IconQuestTexture"]
    if questTexture then questTexture:Hide() end
    local cooldown = _G[button:GetName() .. "Cooldown"]
    if cooldown then cooldown:Hide() end
end

-- Blizzard's backpack numbers slots in reverse visual order. Preserve that mapping
-- so our first stored item appears in the backpack's top-left slot.
for visualIndex = 1, MAX_SLOTS do
    local button = _G[FRAME_NAME .. "Item" .. visualIndex]
    local stashIndex = MAX_SLOTS - visualIndex + 1
    button:SetID(stashIndex)
    ConfigureSlot(button, visualIndex)
    SLOTS[stashIndex] = button
end

for visualIndex = MAX_SLOTS + 1, 36 do
    local button = _G[FRAME_NAME .. "Item" .. visualIndex]
    if button then button:Hide() end
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
        SetItemButtonTexture(button, nil)
        SetItemButtonCount(button, 0)
        SetItemButtonDesaturated(button, false)
        return
    end

    local texture = GetItemIcon(item.entry) or "Interface\\Icons\\INV_Misc_QuestionMark"
    SetItemButtonTexture(button, texture)
    SetItemButtonCount(button, item.count)
    SetItemButtonDesaturated(button, false)
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

-- The current server snapshot travels as hidden-looking system messages. Consume
-- them here so the protocol never appears in the player's chat window.
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
