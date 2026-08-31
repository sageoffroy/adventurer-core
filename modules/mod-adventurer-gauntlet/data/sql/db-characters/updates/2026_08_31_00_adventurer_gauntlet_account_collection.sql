CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_account_collection` (
  `account_id` INT UNSIGNED NOT NULL,
  `item_entry` INT UNSIGNED NOT NULL,
  `discovered_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`account_id`, `item_entry`),
  KEY `idx_adventurer_gauntlet_collection_item` (`item_entry`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
