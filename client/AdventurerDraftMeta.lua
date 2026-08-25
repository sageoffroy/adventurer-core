-- Adventurer SpellDraft meta-actions: reroll, bless and destroy.
-- Loaded after AdventurerResources.lua so the existing three-card frame is the
-- single source of truth for choosing cards. This layer only wraps card clicks
-- while an explicit meta-action mode is active.

local ADVENTURER_CLASS_ID = 10
local DRAFT_PREFIX = "AdventurerDraft"
local DRAFT_REROLL_MESSAGE = "ADRAFT_REROLL"
local DRAFT_BLESS_PREFIX = "ADRAFT_BLESS:"
local DRAFT_DESTROY_PREFIX = "ADRAFT_DESTROY:"

local locale = GetLocale()
local text
if locale == "esES" or locale == "esMX" then
    text = {
        reroll = "Relanzar",
        bless = "Bendecir",
        destroy = "Destruir",
        cancel = "Cancelar",
        rerolls = "Relanzamientos: %d",
        destroys = "Destrucciones: %d",
        blessed = "Bendecida x%.1f",
        blessHint = "Selecciona una carta para bendecirla",
        destroyHint = "Selecciona una carta para destruirla",
    }
else
    text = {
        reroll = "Reroll",
        bless = "Bless",
        destroy = "Destroy",
        cancel = "Cancel",
        rerolls = "Rerolls: %d",
        destroys = "Destroys: %d",
        blessed = "Blessed x%.1f",
        blessHint = "Select a card to bless it",
        destroyHint = "Select a card to destroy it",
    }
end

local function IsAdventurer()
    local className, classToken, classId = UnitClass("player")
    if classId == ADVENTURER_CLASS_ID or classToken == "ADVENTURER" then
        return true
    end
    return className == "Adventurer" or className == "Aventurero" or className == "Aventurera"
end

local function SendDraftCommand(message)
    local target = UnitName("player")
    if target and target ~= "" then
        SendChatMessage(message, "WHISPER", nil, target)
    end
end

local function SplitText(value, separator)
    local parts = {}
    if not value or value == "" then
        return parts
    end
    local start = 1
    while true do
        local first, last = string.find(value, separator, start, true)
        if not first then
            table.insert(parts, string.sub(value, start))
            break
        end
        table.insert(parts, string.sub(value, start, first - 1))
        start = last + 1
    end
    return parts
end

local DraftFrame = AdventurerDraftFrame
if not DraftFrame then
    return
end

-- The original chooser is 300px high and the card buttons end near its bottom.
-- Give meta-actions their own footer instead of overlaying the card content.
DraftFrame:SetHeight(365)
if DraftFrame.hint then
    DraftFrame.hint:ClearAllPoints()
    DraftFrame.hint:SetPoint("BOTTOM", DraftFrame, "BOTTOM", 0, 76)
end

local state = {
    rerolls = 0,
    destroys = 0,
    blessedCardId = 0,
    blessMultiplierPercent = 0,
    mode = nil,
    offered = {},
}

DraftFrame.metaStatus = DraftFrame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
DraftFrame.metaStatus:SetPoint("BOTTOM", DraftFrame, "BOTTOM", 0, 56)
DraftFrame.metaStatus:SetText("")

local function CreateActionButton(name, x)
    local button = CreateFrame("Button", name, DraftFrame, "UIPanelButtonTemplate")
    button:SetWidth(112)
    button:SetHeight(24)
    button:SetPoint("BOTTOM", DraftFrame, "BOTTOM", x, 22)
    return button
end

local rerollButton = CreateActionButton("AdventurerDraftRerollButton", -126)
local blessButton = CreateActionButton("AdventurerDraftBlessButton", 0)
local destroyButton = CreateActionButton("AdventurerDraftDestroyButton", 126)

rerollButton:SetText(text.reroll)
blessButton:SetText(text.bless)
destroyButton:SetText(text.destroy)

local cardButtons = {}
for i = 1, 3 do
    local button = _G["AdventurerDraftCard" .. i]
    if button then
        button.adventurerOriginalDraftClick = button:GetScript("OnClick")
        button.adventurerMetaBadge = button:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        button.adventurerMetaBadge:SetPoint("TOPRIGHT", button, "TOPRIGHT", -8, -7)
        button.adventurerMetaBadge:SetText("")
        table.insert(cardButtons, button)
    end
end

local function ResetMode()
    state.mode = nil
    blessButton:SetText(text.bless)
    destroyButton:SetText(text.destroy)
    if DraftFrame.hint then
        if locale == "esES" or locale == "esMX" then
            DraftFrame.hint:SetText("Mouseover: detalles de la habilidad")
        else
            DraftFrame.hint:SetText("Mouseover: ability details")
        end
    end
end

local function RefreshMetaUI()
    local blessMultiplier = (state.blessMultiplierPercent or 0) / 100
    local status = string.format(text.rerolls, state.rerolls)
        .. "   •   "
        .. string.format(text.destroys, state.destroys)
    if state.blessedCardId and state.blessedCardId > 0 and blessMultiplier > 0 then
        status = status .. "   •   " .. string.format(text.blessed, blessMultiplier)
    end
    DraftFrame.metaStatus:SetText(status)

    if state.rerolls > 0 and DraftFrame:IsShown() then
        rerollButton:Enable()
    else
        rerollButton:Disable()
    end

    if state.blessMultiplierPercent > 0 and DraftFrame:IsShown() then
        blessButton:Enable()
    else
        blessButton:Disable()
    end

    if state.destroys > 0 and DraftFrame:IsShown() then
        destroyButton:Enable()
    else
        destroyButton:Disable()
    end

    for _, button in ipairs(cardButtons) do
        if button.cardId and button.cardId == state.blessedCardId then
            button.adventurerMetaBadge:SetText("★")
            button.adventurerMetaBadge:SetTextColor(1, 0.82, 0)
        else
            button.adventurerMetaBadge:SetText("")
        end
    end
end

for _, button in ipairs(cardButtons) do
    button:SetScript("OnClick", function(self, mouseButton)
        if not self.cardId then
            return
        end

        if state.mode == "bless" then
            SendDraftCommand(DRAFT_BLESS_PREFIX .. self.cardId)
            ResetMode()
            return
        end

        if state.mode == "destroy" then
            SendDraftCommand(DRAFT_DESTROY_PREFIX .. self.cardId)
            ResetMode()
            destroyButton:Disable()
            return
        end

        if self.adventurerOriginalDraftClick then
            self.adventurerOriginalDraftClick(self, mouseButton)
        end
    end)
end

rerollButton:SetScript("OnClick", function()
    if state.rerolls <= 0 then
        return
    end
    ResetMode()
    rerollButton:Disable()
    SendDraftCommand(DRAFT_REROLL_MESSAGE)
end)

blessButton:SetScript("OnClick", function()
    if state.mode == "bless" then
        ResetMode()
    else
        state.mode = "bless"
        blessButton:SetText(text.cancel)
        destroyButton:SetText(text.destroy)
        if DraftFrame.hint then
            DraftFrame.hint:SetText(text.blessHint)
        end
    end
end)

destroyButton:SetScript("OnClick", function()
    if state.destroys <= 0 then
        return
    end
    if state.mode == "destroy" then
        ResetMode()
    else
        state.mode = "destroy"
        destroyButton:SetText(text.cancel)
        blessButton:SetText(text.bless)
        if DraftFrame.hint then
            DraftFrame.hint:SetText(text.destroyHint)
        end
    end
end)

local function ParseOffer(message)
    local sections = SplitText(message, "|")
    if #sections < 5 or sections[1] ~= "O" then
        return
    end
    state.offered = {}
    local records = SplitText(sections[5], ";")
    for _, record in ipairs(records) do
        local fields = SplitText(record, ":")
        local cardId = tonumber(fields[1])
        if cardId then
            table.insert(state.offered, cardId)
        end
    end
end

local function ParseMeta(message)
    local fields = SplitText(message, "|")
    if #fields < 5 or fields[1] ~= "M" then
        return
    end
    state.rerolls = tonumber(fields[2]) or 0
    state.destroys = tonumber(fields[3]) or 0
    state.blessedCardId = tonumber(fields[4]) or 0
    state.blessMultiplierPercent = tonumber(fields[5]) or 0
    RefreshMetaUI()
end

local function MetaWhisperFilter(_, _, message, sender)
    if not IsAdventurer() or sender ~= UnitName("player") then
        return false
    end
    if message == DRAFT_REROLL_MESSAGE then
        return true
    end
    if string.sub(message, 1, string.len(DRAFT_BLESS_PREFIX)) == DRAFT_BLESS_PREFIX then
        return true
    end
    if string.sub(message, 1, string.len(DRAFT_DESTROY_PREFIX)) == DRAFT_DESTROY_PREFIX then
        return true
    end
    return false
end

ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER", MetaWhisperFilter)
ChatFrame_AddMessageEventFilter("CHAT_MSG_WHISPER_INFORM", MetaWhisperFilter)

local MetaEventFrame = CreateFrame("Frame", "AdventurerDraftMetaEventFrame", UIParent)
MetaEventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
MetaEventFrame:RegisterEvent("CHAT_MSG_ADDON")
MetaEventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "PLAYER_ENTERING_WORLD" then
        ResetMode()
        RefreshMetaUI()
        return
    end

    local prefix, message = ...
    if not IsAdventurer() or prefix ~= DRAFT_PREFIX or not message then
        return
    end

    if string.sub(message, 1, 2) == "O|" then
        ParseOffer(message)
        ResetMode()
        RefreshMetaUI()
    elseif string.sub(message, 1, 2) == "M|" then
        ParseMeta(message)
    elseif message == "C" then
        ResetMode()
        RefreshMetaUI()
    elseif string.sub(message, 1, 2) == "E|" then
        ResetMode()
        RefreshMetaUI()
    end
end)
