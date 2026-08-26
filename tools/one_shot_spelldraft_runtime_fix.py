from pathlib import Path


def replace(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {count}: {old[:80]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


core = "payload/core/src/server/scripts/Custom/adventurer_core.cpp"
client = "client/AdventurerDraftMeta.lua"
config = "config/spelldraft/spelldraft.conf"
tests = "tests/test_spelldraft_v1.py"

replace(core, "constexpr uint32 ADVENTURER_DRAFT_SCHEMA = 2;", "constexpr uint32 ADVENTURER_DRAFT_SCHEMA = 3;")
replace(core, "    uint8 initialActiveSourceLevelCap = 8;", "    uint8 initialActiveSourceLevelCap = 10;")
replace(core, "    uint16 rerollStartingCharges = 2;", "    uint16 rerollStartingCharges = 10;")
replace(
    core,
    "    uint8 blessMaxActive = 1;\n    uint32 blessWeightMultiplierPercent = 300;",
    "    uint16 blessStartingCharges = 1;\n"
    "    uint8 blessGainEveryLevels = 10;\n"
    "    uint16 blessGainAmount = 1;\n"
    "    uint16 blessMaxCharges = 0;\n"
    "    uint8 blessMaxActive = 1;\n"
    "    uint32 blessWeightMultiplierPercent = 300;",
)
replace(
    core,
    "    uint16 rerollCharges = 0;\n    uint16 destroyCharges = 0;",
    "    uint16 rerollCharges = 0;\n    uint16 blessCharges = 0;\n    uint16 destroyCharges = 0;",
)
replace(
    core,
    '    parsed.blessMaxActive = static_cast<uint8>(ReadOption(values, "Bless.MaxActive", parsed.blessMaxActive));\n'
    '    parsed.blessWeightMultiplierPercent = ReadOption(values, "Bless.WeightMultiplierPercent", parsed.blessWeightMultiplierPercent);',
    '    parsed.blessStartingCharges = static_cast<uint16>(ReadOption(values, "Bless.StartingCharges", parsed.blessStartingCharges));\n'
    '    parsed.blessGainEveryLevels = static_cast<uint8>(ReadOption(values, "Bless.GainEveryLevels", parsed.blessGainEveryLevels));\n'
    '    parsed.blessGainAmount = static_cast<uint16>(ReadOption(values, "Bless.GainAmount", parsed.blessGainAmount));\n'
    '    parsed.blessMaxCharges = static_cast<uint16>(ReadOption(values, "Bless.MaxCharges", parsed.blessMaxCharges));\n'
    '    parsed.blessMaxActive = static_cast<uint8>(ReadOption(values, "Bless.MaxActive", parsed.blessMaxActive));\n'
    '    parsed.blessWeightMultiplierPercent = ReadOption(values, "Bless.WeightMultiplierPercent", parsed.blessWeightMultiplierPercent);',
)
replace(
    core,
    "// v2: schema,level,pendingA,pendingT,type,o1,o2,o3,rerolls,destroys,blessed,\n//     oCARD:RANK...,xCARD...",
    "// v2: schema,level,pendingA,pendingT,type,o1,o2,o3,rerolls,destroys,blessed,\n"
    "//     oCARD:RANK...,xCARD...\n"
    "// v3: schema,level,pendingA,pendingT,type,o1,o2,o3,rerolls,blesses,destroys,\n"
    "//     blessed,oCARD:RANK...,xCARD...",
)
replace(
    core,
    "        << ',' << state.rerollCharges\n        << ',' << state.destroyCharges\n        << ',' << state.blessedCardId;",
    "        << ',' << state.rerollCharges\n        << ',' << state.blessCharges\n        << ',' << state.destroyCharges\n        << ',' << state.blessedCardId;",
)
replace(
    core,
    "        if (schema != 1 && schema != ADVENTURER_DRAFT_SCHEMA)\n            return false;",
    "        if (schema != 1 && schema != 2 && schema != ADVENTURER_DRAFT_SCHEMA)\n            return false;",
)
replace(
    core,
    """        size_t firstDynamic = 8;
        if (schema == ADVENTURER_DRAFT_SCHEMA)
        {
            if (tokens.size() < 11)
                return false;
            state.rerollCharges = static_cast<uint16>(std::stoul(tokens[8]));
            state.destroyCharges = static_cast<uint16>(std::stoul(tokens[9]));
            state.blessedCardId = static_cast<uint32>(std::stoul(tokens[10]));
            firstDynamic = 11;
        }
        else
        {
            state.rerollCharges = GetDraftConfig().rerollStartingCharges;
            state.destroyCharges = GetDraftConfig().destroyStartingCharges;
        }""",
    """        size_t firstDynamic = 8;
        if (schema == ADVENTURER_DRAFT_SCHEMA)
        {
            if (tokens.size() < 12)
                return false;
            state.rerollCharges = static_cast<uint16>(std::stoul(tokens[8]));
            state.blessCharges = static_cast<uint16>(std::stoul(tokens[9]));
            state.destroyCharges = static_cast<uint16>(std::stoul(tokens[10]));
            state.blessedCardId = static_cast<uint32>(std::stoul(tokens[11]));
            firstDynamic = 12;
        }
        else if (schema == 2)
        {
            if (tokens.size() < 11)
                return false;
            state.rerollCharges = static_cast<uint16>(std::stoul(tokens[8]));
            state.blessCharges = GetDraftConfig().blessStartingCharges;
            state.destroyCharges = static_cast<uint16>(std::stoul(tokens[9]));
            state.blessedCardId = static_cast<uint32>(std::stoul(tokens[10]));
            firstDynamic = 11;
        }
        else
        {
            state.rerollCharges = GetDraftConfig().rerollStartingCharges;
            state.blessCharges = GetDraftConfig().blessStartingCharges;
            state.destroyCharges = GetDraftConfig().destroyStartingCharges;
        }""",
)
replace(
    core,
    "    if (config.rerollGainEveryLevels > 0 && level > 1 && (level % config.rerollGainEveryLevels) == 0)\n"
    "        AddCharge(state.rerollCharges, config.rerollGainAmount, config.rerollMaxCharges);\n"
    "    if (config.destroyGainEveryLevels > 0 && level > 1 && (level % config.destroyGainEveryLevels) == 0)",
    "    if (config.rerollGainEveryLevels > 0 && level > 1 && (level % config.rerollGainEveryLevels) == 0)\n"
    "        AddCharge(state.rerollCharges, config.rerollGainAmount, config.rerollMaxCharges);\n"
    "    if (config.blessGainEveryLevels > 0 && level > 1 && (level % config.blessGainEveryLevels) == 0)\n"
    "        AddCharge(state.blessCharges, config.blessGainAmount, config.blessMaxCharges);\n"
    "    if (config.destroyGainEveryLevels > 0 && level > 1 && (level % config.destroyGainEveryLevels) == 0)",
)
replace(
    core,
    "    state.pendingActive = config.initialActivePicks;\n    state.rerollCharges = config.rerollStartingCharges;\n    state.destroyCharges = config.destroyStartingCharges;",
    "    state.pendingActive = config.initialActivePicks;\n    state.rerollCharges = config.rerollStartingCharges;\n    state.blessCharges = config.blessStartingCharges;\n    state.destroyCharges = config.destroyStartingCharges;",
)
replace(
    core,
    """void SendDraftMeta(Player* player, DraftState const& state)
{
    std::ostringstream payload;
    payload << "M|" << state.rerollCharges
            << '|' << state.destroyCharges
            << '|' << state.blessedCardId
            << '|' << (GetDraftConfig().blessMaxActive > 0 ? GetDraftConfig().blessWeightMultiplierPercent : 0);
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, payload.str());
}""",
    """void SendDraftMeta(Player* player, DraftState const& state)
{
    DraftRuntimeConfig const& config = GetDraftConfig();
    std::ostringstream payload;
    payload << "M|" << state.rerollCharges
            << '|' << state.destroyCharges
            << '|' << state.blessedCardId
            << '|' << (config.blessMaxActive > 0 ? config.blessWeightMultiplierPercent : 0)
            << '|' << state.blessCharges
            << '|' << config.rerollStartingCharges
            << '|' << config.blessStartingCharges
            << '|' << config.destroyStartingCharges
            << '|' << uint32(config.initialActiveSourceLevelCap)
            << '|' << GetDraftCards().size();
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, payload.str());
}""",
)
replace(
    core,
    """    DraftCard const* card = FindDraftCard(cardId);
    if (!card || !IsCardInCurrentOffer(state, cardId) || !IsCardEligible(player, state, *card, state.offerType))
    {
        SendDraftError(player, "INVALID_BLESS", &state);
        return;
    }

    state.blessedCardId = cardId;""",
    """    if (state.blessCharges == 0)
    {
        SendDraftError(player, "NO_BLESSES", &state);
        return;
    }

    DraftCard const* card = FindDraftCard(cardId);
    if (!card || !IsCardInCurrentOffer(state, cardId) || !IsCardEligible(player, state, *card, state.offerType))
    {
        SendDraftError(player, "INVALID_BLESS", &state);
        return;
    }

    --state.blessCharges;
    state.blessedCardId = cardId;""",
)

replace(
    config,
    "[Reroll]\n# Prototype defaults only; these are balance knobs, not closed design values.\nStartingCharges = 2",
    "[Reroll]\n# Prototype defaults only; these are balance knobs, not closed design values.\nStartingCharges = 10",
)

replace(client, 'blessings = "Bendiciones: %s"', 'blessings = "Bendiciones: %d"')
replace(client, 'blessings = "Blessings: %s"', 'blessings = "Blessings: %d"')
replace(client, "    rerolls = 0,\n    destroys = 0,", "    rerolls = 0,\n    blesses = 0,\n    destroys = 0,")
replace(
    client,
    "    pendingPickedCardId = nil,\n}",
    "    pendingPickedCardId = nil,\n"
    "    serverConfigKnown = false,\n"
    "    serverRerollStart = 0,\n"
    "    serverBlessStart = 0,\n"
    "    serverDestroyStart = 0,\n"
    "    serverSourceCap = 0,\n"
    "    serverCatalogSize = 0,\n}",
)
replace(
    client,
    'debugFrame.title:SetText(text.debugTitle)\n\ndebugFrame.hint = debugFrame:CreateFontString',
    'debugFrame.title:SetText(text.debugTitle)\n\n'
    'debugFrame.runtime = debugFrame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")\n'
    'debugFrame.runtime:SetPoint("TOP", debugFrame, "TOP", 0, -43)\n'
    'debugFrame.runtime:SetText("")\n\n'
    'debugFrame.hint = debugFrame:CreateFontString',
)
replace(
    client,
    'local function RefreshDebugPool()\n    activeColumn.items = BuildDebugList("active")',
    'local function RefreshDebugPool()\n'
    '    if state.serverConfigKnown then\n'
    '        debugFrame.runtime:SetText(string.format("Server config: R%d B%d D%d  cap %d  catalog %d", state.serverRerollStart, state.serverBlessStart, state.serverDestroyStart, state.serverSourceCap, state.serverCatalogSize))\n'
    '    else\n'
    '        debugFrame.runtime:SetText("Server config: old SpellDraft runtime / no report")\n'
    '    end\n'
    '    activeColumn.items = BuildDebugList("active")',
)
replace(
    client,
    '    local blessMultiplier = (state.blessMultiplierPercent or 0) / 100\n'
    '    local blessingCount = state.blessMultiplierPercent > 0 and "∞" or "0"\n'
    '    local status = string.format(text.rerolls, state.rerolls)\n'
    '        .. "   •   "\n'
    '        .. string.format(text.blessings, blessingCount)',
    '    local blessMultiplier = (state.blessMultiplierPercent or 0) / 100\n'
    '    local status = string.format(text.rerolls, state.rerolls)\n'
    '        .. "   •   "\n'
    '        .. string.format(text.blessings, state.blesses)',
)
replace(
    client,
    '    if state.blessMultiplierPercent > 0 and DraftFrame:IsShown() then blessButton:Enable() else blessButton:Disable() end',
    '    if state.blesses > 0 and state.blessMultiplierPercent > 0 and DraftFrame:IsShown() then blessButton:Enable() else blessButton:Disable() end',
)
replace(
    client,
    'blessButton:SetScript("OnClick", function()\n    if state.mode == "bless" then',
    'blessButton:SetScript("OnClick", function()\n    if state.blesses <= 0 then return end\n    if state.mode == "bless" then',
)
replace(
    client,
    "    state.rerolls = tonumber(fields[2]) or 0\n"
    "    state.destroys = tonumber(fields[3]) or 0\n"
    "    state.blessedCardId = tonumber(fields[4]) or 0\n"
    "    state.blessMultiplierPercent = tonumber(fields[5]) or 0\n"
    "    RefreshMetaUI()",
    "    state.rerolls = tonumber(fields[2]) or 0\n"
    "    state.destroys = tonumber(fields[3]) or 0\n"
    "    state.blessedCardId = tonumber(fields[4]) or 0\n"
    "    state.blessMultiplierPercent = tonumber(fields[5]) or 0\n"
    "    state.blesses = tonumber(fields[6]) or 0\n"
    "    state.serverConfigKnown = #fields >= 11\n"
    "    state.serverRerollStart = tonumber(fields[7]) or 0\n"
    "    state.serverBlessStart = tonumber(fields[8]) or 0\n"
    "    state.serverDestroyStart = tonumber(fields[9]) or 0\n"
    "    state.serverSourceCap = tonumber(fields[10]) or 0\n"
    "    state.serverCatalogSize = tonumber(fields[11]) or 0\n"
    "    RefreshMetaUI()",
)

replace(
    tests,
    '    def test_meta_ui_reports_unlimited_blessing_and_has_debug_pool_viewer(self) -> None:\n'
    '        self.assertIn(\'blessings = "Bendiciones: %s"\', self.meta_client)\n'
    '        self.assertIn(\'local blessingCount = state.blessMultiplierPercent > 0 and "∞" or "0"\', self.meta_client)',
    '    def test_meta_ui_reports_finite_blessing_and_has_debug_pool_viewer(self) -> None:\n'
    '        self.assertIn(\'blessings = "Bendiciones: %d"\', self.meta_client)\n'
    '        self.assertIn(\'state.blesses > 0\', self.meta_client)\n'
    '        self.assertNotIn(\'"∞"\', self.meta_client)',
)

print("SpellDraft runtime patch applied successfully")
