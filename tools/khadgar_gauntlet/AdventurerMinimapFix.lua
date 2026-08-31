-- Keep all Blizzard minimap controls untouched. Only move the custom SpellDraft
-- button slightly outside the left rim so it does not overlap the stock tracker.
-- The tracking border is centered on the icon itself; the icon is not moved.
local function RepositionAdventurerDraftButton()
    local draft = _G["AdventurerDraftMinimapButton"]
    local minimap = _G["Minimap"]
    if not draft or not minimap then return end

    draft:ClearAllPoints()
    draft:SetPoint("RIGHT", minimap, "LEFT", 6, -18)

    if draft.border and draft.icon then
        draft.border:ClearAllPoints()
        draft.border:SetPoint("CENTER", draft.icon, "CENTER", 0, 0)
    end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:SetScript("OnEvent", function()
    RepositionAdventurerDraftButton()
end)

RepositionAdventurerDraftButton()
