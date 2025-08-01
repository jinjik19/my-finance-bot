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
WITH MonthlyMovements AS (
    -- Доходы из таблицы 'transactions' (категория 'income')
    SELECT
        date_trunc('month', tx.transaction_date) AS month_start,
        SUM(tx.amount) AS amount,
        'income' AS type
    FROM
        transactions tx
    JOIN
        categories c ON tx.category_id = c.id
    WHERE
        c.type = 'income'
        AND tx.transaction_date >= {{date_filter}}
    GROUP BY
        month_start

    UNION ALL

    -- Расходы из таблицы 'transactions' (категория 'expense')
    SELECT
        date_trunc('month', tx.transaction_date) AS month_start,
        SUM(tx.amount) AS amount,
        'expense' AS type
    FROM
        transactions tx
    JOIN
        categories c ON tx.category_id = c.id
    WHERE
        c.type = 'expense'
        AND tx.transaction_date >= {{date_filter}}
    GROUP BY
        month_start
)
SELECT
    mm.month_start,
    COALESCE(SUM(CASE WHEN mm.type = 'income' THEN mm.amount ELSE 0 END), 0) AS total_income,
    COALESCE(SUM(CASE WHEN mm.type = 'expense' THEN mm.amount ELSE 0 END), 0) AS total_expense
FROM
    MonthlyMovements mm
GROUP BY
    mm.month_start
ORDER BY
    mm.month_start ASC;


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
SELECT
  e.balance / (
    SELECT
      avg(monthly_sum)
    FROM
      (
        SELECT
          sum(t.amount) AS monthly_sum
        FROM
          transactions AS t
          JOIN categories AS c ON t.category_id = c.id
        WHERE
          c.type = 'expense'
        GROUP BY
          date_trunc('month', t.transaction_date)
      ) AS monthly_expenses
  ) as months_of_safety
FROM
  envelopes AS e
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

    UNION ALL

    -- Поток: Конверт -> Конверт (Переводы)
    SELECT
        ef.name AS "source",
        et.name AS "target",
        t.amount AS "value"
    FROM transfers t
    JOIN envelopes ef ON t.from_envelope_id = ef.id
    JOIN envelopes et ON t.to_envelope_id = et.id
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
WITH MonthlyMovements AS (
    -- Движения в доходный конверт за текущий месяц
    SELECT
        e_inc.id AS envelope_id,
        sum(CASE WHEN c.type = 'income' THEN t.amount ELSE -t.amount END) as net_movement_this_month
    FROM transactions t
    JOIN envelopes e_inc ON t.envelope_id = e_inc.id
    JOIN categories c ON t.category_id = c.id
    WHERE e_inc.owner_id = {{user_id}} AND e_inc.name LIKE '💰 Доход %' AND date_trunc('month', t.transaction_date) = date_trunc('month', NOW())
    GROUP BY e_inc.id

    UNION ALL

    -- Переводы из/в доходный конверт за текущий месяц
    SELECT
        e_from.id AS envelope_id,
        sum(CASE WHEN e_from.id = {{user_id_income_envelope_id}} THEN -t.amount ELSE t.amount END) AS net_movement_this_month
    FROM transfers t
    JOIN envelopes e_from ON t.from_envelope_id = e_from.id
    WHERE e_from.owner_id = {{user_id}} AND e_from.name LIKE '💰 Доход %' AND date_trunc('month', t.transfer_date) = date_trunc('month', NOW())
    GROUP BY e_from.id

    UNION ALL

    SELECT
        e_to.id AS envelope_id,
        sum(CASE WHEN e_to.id = {{user_id_income_envelope_id}} THEN t.amount ELSE -t.amount END) AS net_movement_this_month
    FROM transfers t
    JOIN envelopes e_to ON t.to_envelope_id = e_to.id
    WHERE e_to.owner_id = {{user_id}} AND e_to.name LIKE '💰 Доход %' AND date_trunc('month', t.transfer_date) = date_trunc('month', NOW())
    GROUP BY e_to.id
)
SELECT
    e.balance - COALESCE(SUM(mm.net_movement_this_month), 0) AS "Баланс на начало месяца"
FROM envelopes e
LEFT JOIN MonthlyMovements mm ON e.id = mm.envelope_id
WHERE e.owner_id = {{user_id}} AND e.name LIKE '💰 Доход %'
GROUP BY e.balance;
