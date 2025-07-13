-- ====================================================================
-- Вопрос 1: Расходы по Категориям (для диаграммы "Пирог")
-- ====================================================================
SELECT
    c.name,
    sum(t.amount) as total
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE c.type = 'expense'
-- [[AND {{date_filter}}]] -- Опциональный фильтр по дате
GROUP BY c.name
ORDER BY total DESC;


-- ====================================================================
-- Вопрос 2: Динамика Доходов и Расходов (для графика "Линия")
-- ====================================================================
SELECT
    date_trunc('month', transaction_date)::date as month,
    c.type,
    sum(t.amount) as total
FROM transactions t
JOIN categories c ON t.category_id = c.id
GROUP BY month, c.type
ORDER BY month, c.type;


-- ====================================================================
-- Вопрос 3: Прогресс по Главной Цели (для индикатора "Прогресс")
-- ====================================================================
SELECT
    g.name,
    g.target_amount,
    (SELECT sum(amount) FROM transfers WHERE to_envelope_id = g.linked_envelope_id) as current_amount
FROM goals g
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
