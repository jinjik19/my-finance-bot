-- scripts/clean_db.sql

DELETE FROM scheduled_tasks;
DELETE FROM goals;
DELETE FROM transactions;
DELETE FROM transfers;
DELETE FROM system_state;
DELETE FROM categories;
DELETE FROM envelopes;
DELETE FROM users;

-- Опционально: сбросить последовательности ID, если таблицы пустеют
SELECT setval(pg_get_serial_sequence('scheduled_tasks', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('goals', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('transactions', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('transfers', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('categories', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('envelopes', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('users', 'id'), 1, false);