-- ====================================================================
-- Вопрос 1: Расходы по Категориям (для диаграммы "Пирог")
-- ====================================================================
SELECT
    c.name,
    sum(t.amount) as total
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE c.type = 'expense'
GROUP BY c.name
ORDER BY total DESC;

-- Теперь, когда вы создадите этот SQL-запрос, в панели "Переменные" справа вам нужно будет:
-- Найти переменную date_filter.
-- Установить Тип переменной на "Фильтр по полю".
-- В поле "Поле для фильтрации" выбрать Transactions -> Transaction Date.
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
WITH filtered_transactions AS (
  SELECT *
  FROM transactions
  WHERE {{date_filter}}
)
-- Поток: Доходы -> Конверты
SELECT
  c.name AS "source",
  e.name AS "target",
  sum(t.amount) AS "value"
FROM filtered_transactions t
JOIN categories c ON t.category_id = c.id
JOIN envelopes e ON t.envelope_id = e.id
WHERE c.type = 'income'
GROUP BY c.name, e.name

UNION ALL

-- Поток: Конверты -> Расходы
SELECT
  e.name AS "source",
  c.name AS "target",
  sum(t.amount) AS "value"
FROM filtered_transactions t
JOIN categories c ON t.category_id = c.id
JOIN envelopes e ON t.envelope_id = e.id
WHERE c.type = 'expense'
GROUP BY e.name, c.name

UNION ALL

-- Поток: Конверт -> Конверт (Переводы)
SELECT
  ef.name AS "source",
  et.name AS "target",
  sum(t.amount) AS "value"
FROM transfers t
JOIN envelopes ef ON t.from_envelope_id = ef.id
JOIN envelopes et ON t.to_envelope_id = et.id
-- Для переводов можно добавить отдельный фильтр, если нужно
-- WHERE {{transfer_date_filter}} 
GROUP BY ef.name, et.name;