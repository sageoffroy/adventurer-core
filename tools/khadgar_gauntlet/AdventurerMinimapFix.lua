-- Keep all Blizzard minimap controls untouched. Only move the custom SpellDraft
-- button slightly outside the left rim so it does not overlap the stock tracker.
local function RepositionAdventurerDraftButton()
    local draft = _G["AdventurerDraftMinimapButton"]
    local minimap = _G["Minimap"]
    if not draft or not minimap then return end

    draft:ClearAllPoints()
    draft:SetPoint("RIGHT", minimap, "LEFT", 6, -18)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:SetScript("OnEvent", function()
    RepositionAdventurerDraftButton()
end)

RepositionAdventurerDraftButton()
