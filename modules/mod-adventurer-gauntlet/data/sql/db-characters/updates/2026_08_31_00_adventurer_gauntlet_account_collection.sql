CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_account_collection` (
  `account_id` INT UNSIGNED NOT NULL,
  `item_entry` INT UNSIGNED NOT NULL,
  `first_character_guid` INT UNSIGNED NOT NULL DEFAULT 0,
  `discovered_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`account_id`, `item_entry`),
  KEY `idx_item_entry` (`item_entry`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
