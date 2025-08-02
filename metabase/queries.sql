-- ====================================================================
-- Вопрос 1: Расходы по Категориям (для диаграммы "Пирог")
-- ====================================================================
WITH filtered_transactions AS (
  SELECT *
  FROM transactions
  WHERE {{date_filter}}
)
SELECT
    c.name,
    sum(t.amount) as total
FROM filtered_transactions t
JOIN categories c ON t.category_id = c.id
WHERE c.type = 'expense'
GROUP BY c.name
ORDER BY total DESC;


-- ====================================================================
-- Вопрос 2: Динамика Доходов и Расходов (для графика "Комбинированный")
-- ====================================================================
WITH all_flows AS (
    -- Поток: Доходы -> Конверты (из transactions)
    SELECT
        c.name AS "source",
        e.name AS "target",
        t.amount AS "value"
    FROM transactions t
    JOIN categories c ON t.category_id = c.id
    JOIN envelopes e ON t.envelope_id = e.id
    WHERE c.type = 'income'
    AND t.transaction_date BETWEEN {{start_date}} AND {{end_date}} -- <-- ДОБАВЛЕНО: фильтр по дате

    UNION ALL

    -- Поток: Конверты -> Расходы (из transactions)
    SELECT
        e.name AS "source",
        c.name AS "target",
        t.amount AS "value"
    FROM transactions t
    JOIN categories c ON t.category_id = c.id
    JOIN envelopes e ON t.envelope_id = e.id
    WHERE c.type = 'expense'
    AND t.transaction_date BETWEEN {{start_date}} AND {{end_date}} -- <-- ДОБАВЛЕНО: фильтр по дате

    UNION ALL

    -- Поток: Конверт -> Конверт (Переводы)
    SELECT
        ef.name AS "source",
        et.name AS "target",
        t.amount AS "value"
    FROM transfers t
    JOIN envelopes ef ON t.from_envelope_id = ef.id
    JOIN envelopes et ON t.to_envelope_id = et.id
    AND t.transfer_date BETWEEN {{start_date}} AND {{end_date}} -- <-- ДОБАВЛЕНО: фильтр по дате
)
SELECT
    "source",
    "target",
    SUM("value") AS "value"
FROM all_flows
GROUP BY "source", "target"
ORDER BY SUM("value") DESC;


-- ====================================================================
-- Вопрос 3: Прогресс по Главной Цели (для индикатора "Прогресс")
-- ====================================================================
SELECT
    sum(t.amount) as current_amount
FROM transfers t
JOIN goals g ON t.to_envelope_id = g.linked_envelope_id
JOIN system_state ss ON g.phase_id = ss.current_phase_id
WHERE g.status = 'active';


-- ====================================================================
-- Вопрос 4: Подушка Безопасности в месяцах (для индикатора "Число")
-- ====================================================================
WITH
  monthly_expenses_sums AS (
    SELECT
      date_trunc('month', t.transaction_date) AS month,
      SUM(t.amount) AS monthly_sum
    FROM
      transactions AS t
      JOIN categories AS c ON t.category_id = c.id
    WHERE
      c.type = 'expense'
    GROUP BY
      month
  ),
  avg_monthly_expenses AS (
    SELECT
      AVG(monthly_sum) AS avg_sum
    FROM
      monthly_expenses_sums
  )
SELECT
  e.balance / CASE WHEN avg_monthly_expenses.avg_sum > 0 THEN avg_monthly_expenses.avg_sum ELSE 1 END AS "months_of_safety"
FROM
  envelopes AS e
CROSS JOIN
  avg_monthly_expenses
WHERE
  e.name = '🛡️ Подушка безопасности';

-- ====================================================================
-- Вопрос 5: Движение средств (для диаграммы "Sankey")
-- ====================================================================
-- Поток: Доходы -> Конверты
WITH all_flows AS (
    -- Поток: Доходы -> Конверты (из transactions)
    SELECT
        c.name AS "source",
        e.name AS "target",
        t.amount AS "value"
    FROM transactions t
    JOIN categories c ON t.category_id = c.id
    JOIN envelopes e ON t.envelope_id = e.id
    WHERE c.type = 'income'
    AND t.transaction_date BETWEEN {{start_date}} AND {{end_date}} -- <-- ДОБАВЛЕНО: фильтр по дате

    UNION ALL

    -- Поток: Конверты -> Расходы (из transactions)
    SELECT
        e.name AS "source",
        c.name AS "target",
        t.amount AS "value"
    FROM transactions t
    JOIN categories c ON t.category_id = c.id
    JOIN envelopes e ON t.envelope_id = e.id
    WHERE c.type = 'expense'
    AND t.transaction_date BETWEEN {{start_date}} AND {{end_date}} -- <-- ДОБАВЛЕНО: фильтр по дате

    UNION ALL

    -- Поток: Конверт -> Конверт (Переводы)
    SELECT
        ef.name AS "source",
        et.name AS "target",
        t.amount AS "value"
    FROM transfers t
    JOIN envelopes ef ON t.from_envelope_id = ef.id
    JOIN envelopes et ON t.to_envelope_id = et.id
    AND t.transfer_date BETWEEN {{start_date}} AND {{end_date}} -- <-- ДОБАВЛЕНО: фильтр по дате
)
SELECT
    "source",
    "target",
    SUM("value") AS "value"
FROM all_flows
GROUP BY "source", "target"
ORDER BY SUM("value") DESC;


-- ====================================================================
-- 6. Динамика чистого капитала
-- Тип визуализации: Область (с накоплением)
-- Что показывает: Рост сберегательных конвертов со временем.
-- ====================================================================
SELECT
    date_trunc('month', t.transfer_date)::date as month,
    e.name as "Сберегательный конверт",
    sum(t.amount) as "Ежемесячное пополнение"
FROM transfers t
JOIN envelopes e ON t.to_envelope_id = e.id
WHERE e.is_savings = TRUE
GROUP BY month, e.name
ORDER BY month;


-- ====================================================================
-- 7. График выгорания цели
-- Тип визуализации: Линия
-- Что показывает: Как уменьшается остаток по главной цели.
-- ====================================================================
WITH monthly_contributions AS (
  SELECT
    date_trunc('month', transfer_date)::date AS month,
    sum(amount) AS monthly_sum
  FROM transfers
  WHERE to_envelope_id = (SELECT id FROM envelopes WHERE name = '🎯 Главная Цель')
  GROUP BY month
)
SELECT
  mc.month,
  (SELECT target_amount FROM goals WHERE name = 'Ипотека') - sum(mc.monthly_sum) OVER (ORDER BY mc.month) as "Остаток по цели"
FROM monthly_contributions mc;


-- ====================================================================
-- 8. Персональный остаток на начало месяца
-- Тип визуализации: Числа
-- ====================================================================

-- Получение остатка на начало месяца для конкретного пользователя
-- Получение остатка на начало месяца для конкретного пользователя
WITH current_month_movements AS (
    -- Поступления в конверт (income transactions)
    SELECT
        t.envelope_id AS envelope_id,
        t.amount AS movement_amount
    FROM transactions t
    WHERE t.envelope_id = 2
    AND t.transaction_date >= date_trunc('month', NOW())
    AND t.transaction_date < date_trunc('month', NOW()) + INTERVAL '1 month'
    AND t.category_id IN (SELECT id FROM categories WHERE type = 'income')

    UNION ALL

    -- Расходы из конверта (expense transactions)
    SELECT
        t.envelope_id AS envelope_id,
        -t.amount AS movement_amount
    FROM transactions t
    WHERE t.envelope_id = {{income_envelope_id}}
    AND t.transaction_date >= date_trunc('month', NOW())
    AND t.transaction_date < date_trunc('month', NOW()) + INTERVAL '1 month'
    AND t.category_id IN (SELECT id FROM categories WHERE type = 'expense')

    UNION ALL

    -- Переводы В конверт
    SELECT
        t.to_envelope_id AS envelope_id,
        t.amount AS movement_amount
    FROM transfers t
    WHERE t.to_envelope_id = {{income_envelope_id}}
    AND t.transfer_date >= date_trunc('month', NOW())
    AND t.transfer_date < date_trunc('month', NOW()) + INTERVAL '1 month'

    UNION ALL

    -- Переводы ИЗ конверта
    SELECT
        t.from_envelope_id AS envelope_id,
        -t.amount AS movement_amount
    FROM transfers t
    WHERE t.from_envelope_id = {{income_envelope_id}}
    AND t.transfer_date >= date_trunc('month', NOW())
    AND t.transfer_date < date_trunc('month', NOW()) + INTERVAL '1 month'
)
SELECT
    e.balance - COALESCE(SUM(mm.movement_amount), 0) AS "Баланс на начало месяца"
FROM envelopes e
LEFT JOIN current_month_movements mm ON e.id = mm.envelope_id
WHERE e.id = {{income_envelope_id}}
GROUP BY e.balance, e.id;
