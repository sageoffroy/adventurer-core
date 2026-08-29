CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_fallen` (
  `guid` INT UNSIGNED NOT NULL,
  `account_id` INT UNSIGNED NOT NULL,
  `fallen_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `map_id` SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  `level` TINYINT UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY (`guid`),
  KEY `idx_account_id` (`account_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_account_items` (
  `account_id` INT UNSIGNED NOT NULL,
  `item_entry` INT UNSIGNED NOT NULL,
  `first_character_guid` INT UNSIGNED NOT NULL,
  `unlocked_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`account_id`, `item_entry`),
  KEY `idx_item_entry` (`item_entry`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
