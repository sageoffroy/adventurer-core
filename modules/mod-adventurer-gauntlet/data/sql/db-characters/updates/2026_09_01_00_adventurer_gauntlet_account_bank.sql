CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_account_bank` (
  `account_id` INT UNSIGNED NOT NULL,
  `purchased_bag_slots` TINYINT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`account_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_account_bank_bags` (
  `account_id` INT UNSIGNED NOT NULL,
  `bag_index` TINYINT UNSIGNED NOT NULL,
  `item_entry` INT UNSIGNED NOT NULL,
  PRIMARY KEY (`account_id`, `bag_index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_account_bank_items` (
  `account_id` INT UNSIGNED NOT NULL,
  `slot_index` SMALLINT UNSIGNED NOT NULL,
  `item_entry` INT UNSIGNED NOT NULL,
  `item_count` INT UNSIGNED NOT NULL DEFAULT 1,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`account_id`, `slot_index`),
  KEY `idx_account_item` (`account_id`, `item_entry`),
  KEY `idx_item_entry` (`item_entry`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO `adventurer_gauntlet_account_bank_items`
  (`account_id`, `slot_index`, `item_entry`, `item_count`, `updated_at`)
SELECT `account_id`, `slot_index`, `item_entry`, `item_count`, `updated_at`
FROM `adventurer_gauntlet_account_stash`;

DROP TABLE IF EXISTS `adventurer_gauntlet_account_stash`;
