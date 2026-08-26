#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "payload/core/src/server/scripts/Custom/adventurer_core.cpp"
CLIENT = ROOT / "client/AdventurerDraftMeta.lua"
TEST = ROOT / "tests/test_spelldraft_authoritative_pool.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def insert_before(text: str, marker: str, insertion: str, label: str) -> str:
    if insertion.strip() in text:
        return text
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(marker, insertion.rstrip() + "\n\n" + marker, 1)


def patch_core(text: str) -> str:
    text = replace_once(
        text,
        'constexpr char DRAFT_DESTROY_PREFIX[] = "ADRAFT_DESTROY:";\n',
        'constexpr char DRAFT_DESTROY_PREFIX[] = "ADRAFT_DESTROY:";\nconstexpr char DRAFT_DEBUG_POOL_MESSAGE[] = "ADRAFT_POOL";\n',
        "core debug command constant",
    )

    debug_eligibility = r'''bool IsCardDebugEligible(Player const* player, DraftState const& state, DraftCard const& card)
{
    if (card.rankGrants.empty() || state.destroyedCards.count(card.id))
        return false;

    uint8 currentRank = GetOwnedRank(state, card.id);
    if (currentRank >= card.rankGrants.size())
        return false;

    uint32 playerLevel = player ? player->GetLevel() : 1;
    DraftRuntimeConfig const& config = GetDraftConfig();
    uint32 sourceCap = playerLevel;
    if (card.type == DraftCardType::Active)
    {
        sourceCap = playerLevel <= config.initialActiveSourceLevelCap
            ? config.initialActiveSourceLevelCap
            : playerLevel + config.activeSourceLevelLookahead;
    }
    else if (card.type == DraftCardType::Talent)
    {
        // The debug window previews the talent pool from the first talent-draft
        // level onward. Actual talent offers remain level-gated by IsCardEligible.
        sourceCap = std::max<uint32>(playerLevel, config.talentDraftFirstLevel);
    }
    else
        return false;

    if (card.sourceLevel > sourceCap)
        return false;

    return MeetsRequirements(state, card);
}'''
    text = insert_before(
        text,
        "uint32 RarityWeightMultiplier(DraftRarity rarity)\n{",
        debug_eligibility,
        "core debug eligibility",
    )

    debug_sender = r'''void SendDraftDebugPool(Player* player, DraftState const& state)
{
    uint32 activeCount = 0;
    uint32 talentCount = 0;

    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX,
        std::string("D|B|") + std::to_string(GetDraftCards().size()));

    for (DraftCard const& card : GetDraftCards())
    {
        if (!IsCardDebugEligible(player, state, card))
            continue;

        uint8 currentRank = GetOwnedRank(state, card.id);
        uint8 nextRank = currentRank + 1;
        if (nextRank == 0 || nextRank > card.rankGrants.size())
            continue;
        std::vector<uint32> const& grants = card.rankGrants[nextRank - 1];
        if (grants.empty())
            continue;

        if (card.type == DraftCardType::Active)
            ++activeCount;
        else if (card.type == DraftCardType::Talent)
            ++talentCount;

        std::ostringstream payload;
        payload << "D|C|" << (card.type == DraftCardType::Active ? 'A' : 'T')
                << '|' << card.id
                << '|' << grants.front()
                << '|' << uint32(card.rarity)
                << '|' << uint32(card.sourceLevel)
                << '|' << uint32(currentRank)
                << '|' << card.rankGrants.size();
        SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, payload.str());
    }

    std::ostringstream end;
    end << "D|E|" << activeCount << '|' << talentCount;
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, end.str());
}'''
    text = insert_before(
        text,
        "void SendDraftMeta(Player* player, DraftState const& state)\n{",
        debug_sender,
        "core debug sender",
    )

    debug_handler = r'''void HandleDraftDebugPool(Player* player)
{
    ReloadDraftRuntimeData();
    DraftState& state = GetDraftState(player);
    QueueDraftProgressionToLevel(state, player->GetLevel());
    PersistDraftState(player, state);
    SendDraftDebugPool(player, state);
}'''
    text = insert_before(
        text,
        "void HandleDraftReady(Player* player)\n{",
        debug_handler,
        "core debug handler",
    )

    text = replace_once(
        text,
        '''        if (msg == DRAFT_REROLL_MESSAGE)\n        {\n            HandleDraftReroll(player);\n            return false;\n        }\n''',
        '''        if (msg == DRAFT_DEBUG_POOL_MESSAGE)\n        {\n            HandleDraftDebugPool(player);\n            return false;\n        }\n        if (msg == DRAFT_REROLL_MESSAGE)\n        {\n            HandleDraftReroll(player);\n            return false;\n        }\n''',
        "core debug chat handler",
    )
    return text


def patch_client(text: str) -> str:
    text = replace_once(
        text,
        'local DRAFT_DESTROY_PREFIX = "ADRAFT_DESTROY:"\n',
        'local DRAFT_DESTROY_PREFIX = "ADRAFT_DESTROY:"\nlocal DRAFT_DEBUG_POOL_MESSAGE = "ADRAFT_POOL"\n',
        "client debug command constant",
    )

    text = replace_once(
        text,
        '''local rarityLabels = {\n    common = isSpanish and "Común" or "Common",\n    uncommon = isSpanish and "Poco común" or "Uncommon",\n    rare = isSpanish and "Rara" or "Rare",\n    epic = isSpanish and "Épica" or "Epic",\n    legendary = isSpanish and "Legendaria" or "Legendary",\n}\n''',
        '''local rarityLabels = {\n    common = isSpanish and "Común" or "Common",\n    uncommon = isSpanish and "Poco común" or "Uncommon",\n    rare = isSpanish and "Rara" or "Rare",\n    epic = isSpanish and "Épica" or "Epic",\n    legendary = isSpanish and "Legendaria" or "Legendary",\n}\n\nlocal rarityKeys = {\n    [0] = "common",\n    [1] = "uncommon",\n    [2] = "rare",\n    [3] = "epic",\n    [4] = "legendary",\n}\n''',
        "client rarity key map",
    )

    start_marker = "-- Client-side mirror used only by the debug window. Server cards.csv remains\n"
    end_marker = "local function IsAdventurer()\n"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        if "The pool debug catalog is streamed by the server" not in text:
            raise RuntimeError("client static catalog block anchors not found")
    else:
        text = (
            text[:start]
            + "-- The pool debug catalog is streamed by the server from authoritative cards.csv.\n"
            + "-- No card/talent relationships or rarities are hardcoded client-side.\n"
            + text[end:]
        )

    text = replace_once(
        text,
        '''    serverSourceCap = 0,\n    serverCatalogSize = 0,\n}\n''',
        '''    serverSourceCap = 0,\n    serverCatalogSize = 0,\n    debugCatalog = {},\n    debugCatalogLoading = false,\n}\n''',
        "client debug state",
    )

    owned_start = text.find("local function GetOwnedRank(card)\n")
    debug_frame = text.find("local debugFrame = CreateFrame", owned_start)
    if owned_start >= 0 and debug_frame >= 0:
        text = text[:owned_start] + text[debug_frame:]
    elif "local function GetOwnedRank(card)" in text:
        raise RuntimeError("client old debug eligibility block boundary not found")

    old_build = '''local function BuildDebugList(kind)\n    local items = {}\n    for _, card in ipairs(debugCatalog) do\n        if card.type == kind and IsDebugEligible(card) then\n            local name = GetSpellInfo(card.spell) or ("Spell #" .. card.spell)\n            card.debugName = name\n            table.insert(items, card)\n        end\n    end\n'''
    new_build = '''local function BuildDebugList(kind)\n    local items = {}\n    for _, card in ipairs(state.debugCatalog) do\n        if card.type == kind then\n            local name = GetSpellInfo(card.spell) or ("Spell #" .. card.spell)\n            card.debugName = name\n            table.insert(items, card)\n        end\n    end\n'''
    text = replace_once(text, old_build, new_build, "client server-backed debug list")

    text = replace_once(
        text,
        '''                local rank = GetOwnedRank(card)\n                if card.maxRank and card.maxRank > 1 then\n                    row.meta:SetText(string.format("Lv%d  %d/%d", card.level, rank + 1, card.maxRank))\n                else\n''',
        '''                local rank = card.currentRank or 0\n                if card.maxRank and card.maxRank > 1 then\n                    local nextRank = math.min(rank + 1, card.maxRank)\n                    row.meta:SetText(string.format("Lv%d  %d/%d", card.level, nextRank, card.maxRank))\n                else\n''',
        "client debug rank display",
    )

    old_toggle = '''local function ToggleDebugPool()\n    if debugFrame:IsShown() then\n        debugFrame:Hide()\n    else\n        RefreshDebugPool()\n        debugFrame:Show()\n    end\nend\n'''
    new_toggle = '''local function RequestDebugPool()\n    state.debugCatalog = {}\n    state.debugCatalogLoading = true\n    RefreshDebugPool()\n    SendDraftCommand(DRAFT_DEBUG_POOL_MESSAGE)\nend\n\nlocal function ToggleDebugPool()\n    if debugFrame:IsShown() then\n        debugFrame:Hide()\n    else\n        debugFrame:Show()\n        RequestDebugPool()\n    end\nend\n'''
    text = replace_once(text, old_toggle, new_toggle, "client debug request")

    parse_debug = r'''local function ParseDebugPool(message)
    local fields = SplitText(message, "|")
    if #fields < 2 or fields[1] ~= "D" then return end

    if fields[2] == "B" then
        state.debugCatalog = {}
        state.debugCatalogLoading = true
        if tonumber(fields[3]) then
            state.serverCatalogSize = tonumber(fields[3])
        end
        return
    end

    if fields[2] == "C" and #fields >= 9 then
        local kind = fields[3] == "A" and "active" or (fields[3] == "T" and "talent" or nil)
        local cardId = tonumber(fields[4])
        local spellId = tonumber(fields[5])
        local rarity = rarityKeys[tonumber(fields[6]) or 0] or "common"
        local level = tonumber(fields[7]) or 1
        local currentRank = tonumber(fields[8]) or 0
        local maxRank = tonumber(fields[9]) or 1
        if kind and cardId and spellId then
            table.insert(state.debugCatalog, {
                id = cardId,
                type = kind,
                spell = spellId,
                rarity = rarity,
                level = level,
                currentRank = currentRank,
                maxRank = maxRank,
            })
        end
        return
    end

    if fields[2] == "E" then
        state.debugCatalogLoading = false
        if debugFrame:IsShown() then RefreshDebugPool() end
    end
end'''
    text = insert_before(text, "local function ParseMeta(message)\n", parse_debug, "client debug parser")

    text = replace_once(
        text,
        '''    if message == DRAFT_REROLL_MESSAGE then return true end\n''',
        '''    if message == DRAFT_DEBUG_POOL_MESSAGE then return true end\n    if message == DRAFT_REROLL_MESSAGE then return true end\n''',
        "client debug whisper filter",
    )

    text = replace_once(
        text,
        '''        ParseOffer(message)\n        ResetMode()\n        RefreshMetaUI()\n    elseif string.sub(message, 1, 2) == "M|" then\n''',
        '''        ParseOffer(message)\n        ResetMode()\n        RefreshMetaUI()\n        if debugFrame:IsShown() then RequestDebugPool() end\n    elseif string.sub(message, 1, 2) == "D|" then\n        ParseDebugPool(message)\n    elseif string.sub(message, 1, 2) == "M|" then\n''',
        "client debug addon handler",
    )

    text = replace_once(
        text,
        '''        ResetMode()\n        RefreshMetaUI()\n    elseif string.sub(message, 1, 2) == "E|" then\n''',
        '''        ResetMode()\n        RefreshMetaUI()\n        if debugFrame:IsShown() then RequestDebugPool() end\n    elseif string.sub(message, 1, 2) == "E|" then\n''',
        "client refresh debug after close",
    )

    if "local debugCatalog = {" in text:
        raise RuntimeError("hardcoded debugCatalog survived migration")
    return text


def write_test() -> None:
    TEST.write_text(
        '''from __future__ import annotations\n\nimport unittest\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nCORE = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"\nCLIENT = ROOT / "client" / "AdventurerDraftMeta.lua"\n\n\nclass SpellDraftAuthoritativePoolTests(unittest.TestCase):\n    def test_server_exports_authoritative_debug_pool(self) -> None:\n        text = CORE.read_text(encoding="utf-8")\n        self.assertIn('DRAFT_DEBUG_POOL_MESSAGE[] = "ADRAFT_POOL"', text)\n        self.assertIn("bool IsCardDebugEligible", text)\n        self.assertIn("return MeetsRequirements(state, card);", text)\n        self.assertIn("void SendDraftDebugPool", text)\n        self.assertIn('payload << "D|C|"', text)\n        self.assertIn("HandleDraftDebugPool(player);", text)\n\n    def test_client_has_no_hardcoded_card_or_talent_pool(self) -> None:\n        text = CLIENT.read_text(encoding="utf-8")\n        self.assertNotIn("local debugCatalog = {", text)\n        self.assertNotIn('id=105, type="talent"', text)\n        self.assertIn('DRAFT_DEBUG_POOL_MESSAGE = "ADRAFT_POOL"', text)\n        self.assertIn("local function RequestDebugPool()", text)\n        self.assertIn("local function ParseDebugPool(message)", text)\n        self.assertIn("state.debugCatalog", text)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
        encoding="utf-8",
    )


def main() -> None:
    core = patch_core(CORE.read_text(encoding="utf-8"))
    client = patch_client(CLIENT.read_text(encoding="utf-8"))
    CORE.write_text(core, encoding="utf-8")
    CLIENT.write_text(client, encoding="utf-8")
    write_test()
    print("SpellDraft authoritative pool migration applied")


if __name__ == "__main__":
    main()
