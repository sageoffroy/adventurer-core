#pragma once

#include "Define.h"

class Loot;

namespace AdventurerGauntlet::KnowledgeRewards
{
// One independent 2% roll per eligible creature. On success exactly one
// knowledge item is selected from books/tomes that are at most three levels
// ahead of the current reward level.
bool TryAddDrop(Loot& loot, uint8 rewardLevel);
}
