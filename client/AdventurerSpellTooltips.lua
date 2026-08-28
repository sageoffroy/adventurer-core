-- The builder prepends the reviewed curve from the same source as CalcValue.
-- Keep native range/cost/disease fields and modify only the marked base damage.
local function UpdateIcyTouchTooltip(tooltip)
    local _, second, third = tooltip:GetSpell()
    local spellId = tonumber(third) or tonumber(second)
    local values = spellId and IcyTouchNativeRanks[spellId]
    if not values then return end

    local className, classTag, classId = UnitClass("player")
    if classId == 10 or classTag == "ADVENTURER" or className == "Adventurer"
        or className == "Aventurero" or className == "Aventurera" then
        local level = math.max(1, math.min(80, UnitLevel("player") or 1))
        values = IcyTouchLevels[level]
    end
    local amount = tostring(values[1]) .. "–" .. tostring(values[2])
    local changed = false
    for index = 1, tooltip:NumLines() do
        local line = _G[tooltip:GetName() .. "TextLeft" .. index]
        local text = line and line:GetText()
        if text and string.find(text, IcyTouchDamageMarker, 1, true) then
            line:SetText((string.gsub(text, IcyTouchDamageMarker, amount)))
            changed = true
        end
    end
    if changed then tooltip:Show() end
end

GameTooltip:HookScript("OnTooltipSetSpell", UpdateIcyTouchTooltip)
ItemRefTooltip:HookScript("OnTooltipSetSpell", UpdateIcyTouchTooltip)
