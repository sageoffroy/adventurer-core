#include "RunProgress.h"

#include "DatabaseEnv.h"
#include "Group.h"
#include "ObjectAccessor.h"
#include "Player.h"

namespace AdventurerGauntlet::RunProgress
{
namespace
{
void AbandonPreviousActiveRuns(std::vector<Player*> const& members)
{
    for (Player* member : members)
    {
        if (!member)
            continue;

        CharacterDatabase.DirectExecute(
            "UPDATE `adventurer_gauntlet_runs` r "
            "JOIN `adventurer_gauntlet_run_members` m ON m.`run_id` = r.`run_id` "
            "SET r.`status` = 'abandoned', r.`updated_at` = CURRENT_TIMESTAMP "
            "WHERE m.`character_guid` = {} AND r.`status` = 'active'",
            member->GetGUID().GetCounter());
    }
}
}

bool IsSupportedDungeonMap(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

void StartRun(std::vector<Player*> const& members, std::string const& companyName, uint8 runLevel)
{
    if (members.empty() || !members.front())
        return;

    AbandonPreviousActiveRuns(members);

    Player* leader = members.front();
    if (Group* group = leader->GetGroup())
        if (Player* groupLeader = ObjectAccessor::FindPlayer(group->GetLeaderGUID()))
            leader = groupLeader;

    std::string escapedCompanyName = companyName;
    CharacterDatabase.EscapeString(escapedCompanyName);
    uint32 leaderGuid = leader->GetGUID().GetCounter();

    CharacterDatabase.DirectExecute(
        "INSERT INTO `adventurer_gauntlet_runs` "
        "(`company_name`, `leader_guid`, `party_size`, `run_level`, `current_dungeon`, `current_map`, "
        " `current_checkpoint`, `best_dungeon_reached`, `status`) "
        "VALUES ('{}', {}, {}, {}, 1, {}, 0, 1, 'active')",
        escapedCompanyName,
        leaderGuid,
        uint32(members.size()),
        uint32(runLevel),
        RagefireMapId);

    for (Player* member : members)
    {
        if (!member)
            continue;

        std::string memberName = member->GetName();
        CharacterDatabase.EscapeString(memberName);

        CharacterDatabase.DirectExecute(
            "INSERT INTO `adventurer_gauntlet_run_members` "
            "(`run_id`, `character_guid`, `character_name`, `return_map`, `return_x`, `return_y`, `return_z`, `return_o`, "
            " `last_map`, `last_x`, `last_y`, `last_z`, `last_o`) "
            "SELECT `run_id`, {}, '{}', {}, {}, {}, {}, {}, {}, {}, {}, {}, {} "
            "FROM `adventurer_gauntlet_runs` "
            "WHERE `leader_guid` = {} AND `status` = 'active' "
            "ORDER BY `run_id` DESC LIMIT 1",
            member->GetGUID().GetCounter(),
            memberName,
            member->GetMapId(),
            member->GetPositionX(),
            member->GetPositionY(),
            member->GetPositionZ(),
            member->GetOrientation(),
            member->GetMapId(),
            member->GetPositionX(),
            member->GetPositionY(),
            member->GetPositionZ(),
            member->GetOrientation(),
            leaderGuid);
    }
}

void AdvanceDungeon(Player* player, uint8 dungeonIndex, uint32 mapId)
{
    if (!player)
        return;

    CharacterDatabase.DirectExecute(
        "UPDATE `adventurer_gauntlet_runs` r "
        "JOIN `adventurer_gauntlet_run_members` m ON m.`run_id` = r.`run_id` "
        "SET r.`current_dungeon` = {}, r.`current_map` = {}, r.`current_checkpoint` = 0, "
        "    r.`best_dungeon_reached` = GREATEST(r.`best_dungeon_reached`, {}), "
        "    r.`updated_at` = CURRENT_TIMESTAMP "
        "WHERE m.`character_guid` = {} AND r.`status` = 'active'",
        uint32(dungeonIndex),
        mapId,
        uint32(dungeonIndex),
        player->GetGUID().GetCounter());
}

void SaveCheckpoint(Player* player, uint32 checkpoint)
{
    if (!player)
        return;

    CharacterDatabase.DirectExecute(
        "UPDATE `adventurer_gauntlet_runs` r "
        "JOIN `adventurer_gauntlet_run_members` m ON m.`run_id` = r.`run_id` "
        "SET r.`current_checkpoint` = {}, r.`updated_at` = CURRENT_TIMESTAMP "
        "WHERE m.`character_guid` = {} AND r.`status` = 'active'",
        checkpoint,
        player->GetGUID().GetCounter());
}

void MarkMemberFallen(Player* player, bool runEnded)
{
    if (!player)
        return;

    CharacterDatabase.DirectExecute(
        "UPDATE `adventurer_gauntlet_run_members` m "
        "JOIN `adventurer_gauntlet_runs` r ON r.`run_id` = m.`run_id` "
        "SET m.`is_fallen` = 1, m.`updated_at` = CURRENT_TIMESTAMP "
        "WHERE m.`character_guid` = {} AND r.`status` = 'active'",
        player->GetGUID().GetCounter());

    if (runEnded)
        CharacterDatabase.DirectExecute(
            "UPDATE `adventurer_gauntlet_runs` r "
            "JOIN `adventurer_gauntlet_run_members` m ON m.`run_id` = r.`run_id` "
            "SET r.`status` = 'fallen', r.`updated_at` = CURRENT_TIMESTAMP "
            "WHERE m.`character_guid` = {} AND r.`status` = 'active'",
            player->GetGUID().GetCounter());
}

bool LoadActiveRun(Player* player, ActiveRun& run)
{
    if (!player)
        return false;

    QueryResult result = CharacterDatabase.Query(
        "SELECT r.`company_name`, r.`run_level`, r.`current_dungeon`, r.`current_checkpoint`, "
        "       m.`return_map`, m.`return_x`, m.`return_y`, m.`return_z`, m.`return_o` "
        "FROM `adventurer_gauntlet_runs` r "
        "JOIN `adventurer_gauntlet_run_members` m ON m.`run_id` = r.`run_id` "
        "WHERE m.`character_guid` = {} AND r.`status` = 'active' "
        "ORDER BY r.`run_id` DESC LIMIT 1",
        player->GetGUID().GetCounter());

    if (!result)
        return false;

    Field* fields = result->Fetch();
    run.CompanyName = fields[0].Get<std::string>();
    run.RunLevel = fields[1].Get<uint8>();
    run.CurrentDungeon = fields[2].Get<uint8>();
    run.CurrentCheckpoint = fields[3].Get<uint32>();
    run.ReturnPoint = {
        fields[4].Get<uint32>(),
        fields[5].Get<float>(),
        fields[6].Get<float>(),
        fields[7].Get<float>(),
        fields[8].Get<float>()
    };
    return true;
}

uint32 LoadCheckpoint(Player* player)
{
    ActiveRun run;
    return LoadActiveRun(player, run) ? run.CurrentCheckpoint : 0;
}

void SaveLogoutPosition(Player* player)
{
    if (!player || !IsSupportedDungeonMap(player->GetMapId()))
        return;

    CharacterDatabase.DirectExecute(
        "UPDATE `adventurer_gauntlet_run_members` m "
        "JOIN `adventurer_gauntlet_runs` r ON r.`run_id` = m.`run_id` "
        "SET m.`last_map` = {}, m.`last_x` = {}, m.`last_y` = {}, "
        "    m.`last_z` = {}, m.`last_o` = {}, m.`updated_at` = CURRENT_TIMESTAMP "
        "WHERE m.`character_guid` = {} AND r.`status` = 'active'",
        player->GetMapId(),
        player->GetPositionX(),
        player->GetPositionY(),
        player->GetPositionZ(),
        player->GetOrientation(),
        player->GetGUID().GetCounter());
}

bool LoadResumePoint(Player* player, ResumePoint& point)
{
    if (!player)
        return false;

    QueryResult result = CharacterDatabase.Query(
        "SELECT r.`current_map`, m.`last_map`, m.`last_x`, m.`last_y`, m.`last_z`, m.`last_o` "
        "FROM `adventurer_gauntlet_runs` r "
        "JOIN `adventurer_gauntlet_run_members` m ON m.`run_id` = r.`run_id` "
        "WHERE m.`character_guid` = {} AND r.`status` = 'active' "
        "ORDER BY r.`run_id` DESC LIMIT 1",
        player->GetGUID().GetCounter());

    if (!result)
        return false;

    Field* fields = result->Fetch();
    point.CurrentMap = fields[0].Get<uint32>();
    if (!IsSupportedDungeonMap(point.CurrentMap))
        return false;

    point.LastPosition = {
        fields[1].Get<uint32>(),
        fields[2].Get<float>(),
        fields[3].Get<float>(),
        fields[4].Get<float>(),
        fields[5].Get<float>()
    };
    point.LastPositionMatchesCurrentMap = point.LastPosition.MapId == point.CurrentMap;
    return true;
}
}
