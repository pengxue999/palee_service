-- Migration: make discount trigger thresholds admin-configurable
-- Adds discount.threshold_value and backfills the previously hardcoded values:
--   MULTI_SUBJECT_MIN_SUBJECTS = 3
--   LATE_REGISTRATION_THRESHOLD_DAYS = 60
-- Run once against the existing database.

ALTER TABLE discount
  ADD COLUMN threshold_value INT NOT NULL DEFAULT 0 AFTER discount_amount;

UPDATE discount SET threshold_value = 3  WHERE discount_description = 'MULTI_SUBJECT';
UPDATE discount SET threshold_value = 60 WHERE discount_description = 'LATE_REGISTRATION';
