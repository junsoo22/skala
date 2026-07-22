-- ==========================================================
-- Day1 과제 1 — 정규화 워크시트 실습용 테이블 생성 · 데이터 적재
-- 대상: telecom DB (public 스키마)
-- 1NF(원본 비정규화 표) → 2NF(부분 종속 제거) → 3NF(이행 종속 제거)
-- 단계별로 테이블 이름을 분리해 동시에 남겨두므로, 각 단계를 순서대로
-- 캡처하면 됨. DBeaver SQL 편집기에 그대로 붙여넣어 실행.
-- ==========================================================

-- ----------------------------------------------------------
-- 0) 재실행 대비 초기화 (자식 → 부모 순서로 DROP)
-- ----------------------------------------------------------
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS order_items_2nf;
DROP TABLE IF EXISTS orders_2nf;
DROP TABLE IF EXISTS products_2nf;
DROP TABLE IF EXISTS order_raw;

-- ==========================================================
-- [1단계] 1NF — 대상 비정규화 표 (PK = order_id + prod_id)
-- ==========================================================
CREATE TABLE order_raw (
  order_id   VARCHAR(10)   NOT NULL,
  order_dt   DATE          NOT NULL,
  cust_id    VARCHAR(10)   NOT NULL,
  cust_name  VARCHAR(50)   NOT NULL,
  prod_id    VARCHAR(10)   NOT NULL,
  prod_name  VARCHAR(50)   NOT NULL,
  unit_price INTEGER       NOT NULL,
  qty        INTEGER       NOT NULL,
  PRIMARY KEY (order_id, prod_id)
);

INSERT INTO order_raw
  (order_id, order_dt,             cust_id, cust_name, prod_id, prod_name, unit_price, qty)
VALUES
  ('O1001', DATE '2024-06-01', 'C01', '김하늘', 'P10', '노트북', 1200000, 1),
  ('O1001', DATE '2024-06-01', 'C01', '김하늘', 'P22', '마우스',   25000, 2),
  ('O1002', DATE '2024-06-03', 'C02', '이준호', 'P10', '노트북', 1200000, 1);

-- 캡처①: 1NF 원본 표 (모든 칸이 원자값, 반복 그룹 없음)
SELECT * FROM order_raw ORDER BY order_id, prod_id;

-- ==========================================================
-- [2단계] 1NF → 2NF — 부분 종속 제거 (order_id/prod_id에만 종속되는 속성 분리)
-- 이 단계에서는 ORDERS_2NF에 cust_name이 아직 남아있어 이행 종속이 해소되지 않은 상태
-- ==========================================================
CREATE TABLE orders_2nf (
  order_id  VARCHAR(10) PRIMARY KEY,
  order_dt  DATE        NOT NULL,
  cust_id   VARCHAR(10) NOT NULL,
  cust_name VARCHAR(50) NOT NULL
);

CREATE TABLE products_2nf (
  prod_id    VARCHAR(10) PRIMARY KEY,
  prod_name  VARCHAR(50) NOT NULL,
  unit_price INTEGER     NOT NULL
);

CREATE TABLE order_items_2nf (
  order_id VARCHAR(10) NOT NULL REFERENCES orders_2nf(order_id),
  prod_id  VARCHAR(10) NOT NULL REFERENCES products_2nf(prod_id),
  qty      INTEGER     NOT NULL,
  PRIMARY KEY (order_id, prod_id)
);

INSERT INTO orders_2nf (order_id, order_dt, cust_id, cust_name) VALUES
  ('O1001', DATE '2024-06-01', 'C01', '김하늘'),
  ('O1002', DATE '2024-06-03', 'C02', '이준호');

INSERT INTO products_2nf (prod_id, prod_name, unit_price) VALUES
  ('P10', '노트북', 1200000),
  ('P22', '마우스', 25000);

INSERT INTO order_items_2nf (order_id, prod_id, qty) VALUES
  ('O1001', 'P10', 1),
  ('O1001', 'P22', 2),
  ('O1002', 'P10', 1);

-- 캡처②: 2NF 단계 3개 테이블
SELECT * FROM orders_2nf     ORDER BY order_id;
SELECT * FROM products_2nf   ORDER BY prod_id;
SELECT * FROM order_items_2nf ORDER BY order_id, prod_id;

-- ==========================================================
-- [3단계] 2NF → 3NF — 이행 종속 제거 (order_id → cust_id → cust_name)
-- CUSTOMERS를 분리하고 ORDERS에서 cust_name 제거
-- ==========================================================
CREATE TABLE customers (
  cust_id   VARCHAR(10) PRIMARY KEY,
  cust_name VARCHAR(50) NOT NULL
);

CREATE TABLE products (
  prod_id    VARCHAR(10) PRIMARY KEY,
  prod_name  VARCHAR(50) NOT NULL,
  unit_price INTEGER     NOT NULL
);

CREATE TABLE orders (
  order_id VARCHAR(10) PRIMARY KEY,
  order_dt DATE        NOT NULL,
  cust_id  VARCHAR(10) NOT NULL REFERENCES customers(cust_id)
);

CREATE TABLE order_items (
  order_id VARCHAR(10) NOT NULL REFERENCES orders(order_id),
  prod_id  VARCHAR(10) NOT NULL REFERENCES products(prod_id),
  qty      INTEGER     NOT NULL,
  PRIMARY KEY (order_id, prod_id)
);

INSERT INTO customers (cust_id, cust_name) VALUES
  ('C01', '김하늘'),
  ('C02', '이준호');

INSERT INTO products (prod_id, prod_name, unit_price) VALUES
  ('P10', '노트북', 1200000),
  ('P22', '마우스', 25000);

INSERT INTO orders (order_id, order_dt, cust_id) VALUES
  ('O1001', DATE '2024-06-01', 'C01'),
  ('O1002', DATE '2024-06-03', 'C02');

INSERT INTO order_items (order_id, prod_id, qty) VALUES
  ('O1001', 'P10', 1),
  ('O1001', 'P22', 2),
  ('O1002', 'P10', 1);

-- 캡처③: 3NF 최종 4개 테이블
SELECT * FROM customers   ORDER BY cust_id;
SELECT * FROM products    ORDER BY prod_id;
SELECT * FROM orders      ORDER BY order_id;
SELECT * FROM order_items ORDER BY order_id, prod_id;

-- 캡처④(선택): 분해된 4개 테이블을 JOIN하면 원본(1NF) 표가 그대로 복원됨을 확인
SELECT
  o.order_id,
  o.order_dt,
  c.cust_id,
  c.cust_name,
  p.prod_id,
  p.prod_name,
  p.unit_price,
  oi.qty
FROM order_items oi
JOIN orders    o ON o.order_id = oi.order_id
JOIN customers c ON c.cust_id  = o.cust_id
JOIN products  p ON p.prod_id  = oi.prod_id
ORDER BY o.order_id, p.prod_id;
