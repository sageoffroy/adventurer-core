-- Adventurer Gauntlet: make the account stash slot-based like a real bag.

ALTER TABLE `adventurer_gauntlet_account_stash`
    ADD COLUMN `slot_index` TINYINT UNSIGNED NULL AFTER `account_id`;

UPDATE `adventurer_gauntlet_account_stash` AS `stash`
JOIN (
    SELECT
        `account_id`,
        `item_entry`,
        ROW_NUMBER() OVER (PARTITION BY `account_id` ORDER BY `item_entry`) AS `slot_index`
    FROM `adventurer_gauntlet_account_stash`
) AS `numbered`
    ON `numbered`.`account_id` = `stash`.`account_id`
   AND `numbered`.`item_entry` = `stash`.`item_entry`
SET `stash`.`slot_index` = `numbered`.`slot_index`;

ALTER TABLE `adventurer_gauntlet_account_stash`
    DROP PRIMARY KEY,
    MODIFY COLUMN `slot_index` TINYINT UNSIGNED NOT NULL,
    ADD PRIMARY KEY (`account_id`, `slot_index`),
    ADD KEY `idx_account_item` (`account_id`, `item_entry`);
