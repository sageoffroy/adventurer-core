-- Keep Blizzard minimap controls untouched. The custom SpellDraft button and
-- its book icon must stay together: use the book's current position as the
-- authoritative one, then center the round button frame and its border there.
local function RepositionAdventurerDraftButton()
    local draft = _G["AdventurerDraftMinimapButton"]
    if not draft or not draft.icon then return end

    local x, y = draft.icon:GetCenter()
    if not x or not y then return end

    local parent = draft:GetParent() or UIParent
    local scale = parent:GetEffectiveScale()
    local uiScale = UIParent:GetEffectiveScale()
    x = x * scale / uiScale
    y = y * scale / uiScale

    draft:ClearAllPoints()
    draft:SetPoint("CENTER", UIParent, "BOTTOMLEFT", x, y)

    draft.icon:ClearAllPoints()
    draft.icon:SetPoint("CENTER", draft, "CENTER", 0, 0)

    if draft.border then
        draft.border:ClearAllPoints()
        draft.border:SetPoint("CENTER", draft, "CENTER", 0, 0)
    end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:SetScript("OnEvent", function()
    RepositionAdventurerDraftButton()
end)

RepositionAdventurerDraftButton()
