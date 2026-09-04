CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_runs` (
  `run_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `company_name` VARCHAR(96) NOT NULL,
  `leader_guid` INT UNSIGNED NOT NULL,
  `party_size` TINYINT UNSIGNED NOT NULL,
  `run_level` TINYINT UNSIGNED NOT NULL,
  `current_dungeon` TINYINT UNSIGNED NOT NULL DEFAULT 1,
  `current_map` INT UNSIGNED NOT NULL DEFAULT 389,
  `current_checkpoint` INT UNSIGNED NOT NULL DEFAULT 0,
  `best_dungeon_reached` TINYINT UNSIGNED NOT NULL DEFAULT 1,
  `status` ENUM('active','fallen','completed','abandoned') NOT NULL DEFAULT 'active',
  `started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`run_id`),
  KEY `idx_gauntlet_runs_status_best` (`status`, `best_dungeon_reached`),
  KEY `idx_gauntlet_runs_leader` (`leader_guid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `adventurer_gauntlet_run_members` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `character_guid` INT UNSIGNED NOT NULL,
  `character_name` VARCHAR(12) NOT NULL,
  `return_map` INT UNSIGNED NOT NULL,
  `return_x` FLOAT NOT NULL,
  `return_y` FLOAT NOT NULL,
  `return_z` FLOAT NOT NULL,
  `return_o` FLOAT NOT NULL,
  `last_map` INT UNSIGNED NOT NULL,
  `last_x` FLOAT NOT NULL,
  `last_y` FLOAT NOT NULL,
  `last_z` FLOAT NOT NULL,
  `last_o` FLOAT NOT NULL,
  `is_fallen` TINYINT UNSIGNED NOT NULL DEFAULT 0,
  `joined_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`run_id`, `character_guid`),
  KEY `idx_gauntlet_member_guid` (`character_guid`, `run_id`),
  CONSTRAINT `fk_gauntlet_member_run`
    FOREIGN KEY (`run_id`) REFERENCES `adventurer_gauntlet_runs` (`run_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
