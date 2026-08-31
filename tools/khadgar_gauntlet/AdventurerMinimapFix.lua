-- Keep the stock tracking button and SpellDraft button as a vertical column on
-- the left minimap rim. FrameXML names are from the stock WotLK 3.3.5a client.
local function RepositionAdventurerMinimapButtons()
    local draft = _G["AdventurerDraftMinimapButton"]
    local minimap = _G["Minimap"]
    if not draft or not minimap then return end

    local tracking = _G["MiniMapTracking"]
    if tracking then
        tracking:ClearAllPoints()
        tracking:SetPoint("TOPLEFT", minimap, "TOPLEFT", 13, -32)

        draft:ClearAllPoints()
        draft:SetPoint("TOPLEFT", minimap, "TOPLEFT", 13, -72)
    else
        draft:ClearAllPoints()
        draft:SetPoint("LEFT", minimap, "LEFT", 0, -20)
    end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("MINIMAP_UPDATE_TRACKING")
frame:SetScript("OnEvent", function()
    RepositionAdventurerMinimapButtons()
end)

RepositionAdventurerMinimapButtons()
