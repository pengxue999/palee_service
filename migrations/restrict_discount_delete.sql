-- Migration: prevent deleting a discount that registrations still reference.
-- Changes registration.discount_id FK from ON DELETE SET NULL to ON DELETE RESTRICT.
--
-- Why: SET NULL let a discount be deleted silently, blanking discount_id on every
-- referencing registration while total_amount/final_amount still reflected the
-- discount -- leaving the discount invisible but its effect baked into the amounts.
--
-- The original FK is unnamed in database_schema.sql, so MySQL auto-named it
-- (typically registration_ibfk_2). Look the name up rather than assuming it.
-- Run once against the existing database.

SELECT CONSTRAINT_NAME INTO @fk
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'registration'
  AND COLUMN_NAME = 'discount_id'
  AND REFERENCED_TABLE_NAME = 'discount';

SET @sql = CONCAT('ALTER TABLE registration DROP FOREIGN KEY ', @fk);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE registration
  ADD CONSTRAINT fk_registration_discount
  FOREIGN KEY (discount_id) REFERENCES discount (discount_id)
  ON DELETE RESTRICT ON UPDATE CASCADE;
