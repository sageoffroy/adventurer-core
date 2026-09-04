ALTER TABLE `adventurer_gauntlet_runs`
  ADD COLUMN `campaign_key` VARCHAR(64) NOT NULL DEFAULT '' AFTER `run_level`;
