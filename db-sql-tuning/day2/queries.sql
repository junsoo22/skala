-- ==========================================================
-- Day2 조별 과제 SQL — DBeaver SQL 편집기에 그대로 붙여넣어 실행
-- 대상: telecom DB (public 스키마) — Day1 산출물 + 03_account.sql 추가 적재 필요
-- 사전 준비: psql -d telecom -f 03_account.sql   (과제6·7 전에 1회)
-- ==========================================================

-- ----------------------------------------------------------
-- [과제 1 · C1] 다중 JOIN
-- subscription⋈customer⋈plan 3테이블 조인, 활성(ACTIVE) 가입 고객명·요금제·월요금을
-- 월요금 내림차순으로 조회
-- ----------------------------------------------------------
SELECT c.name AS cust_name, p.plan_name, p.monthly_fee
FROM subscription s
JOIN customer c ON c.cust_id = s.cust_id
JOIN plan p ON p.plan_id = s.plan_id
WHERE s.status = 'ACTIVE'
ORDER BY p.monthly_fee DESC;

-- ----------------------------------------------------------
-- [과제 2 · C2] OUTER JOIN
-- 가입 이력이 한 번도 없는 고객을 LEFT JOIN + 자식 PK IS NULL로 찾기
-- ----------------------------------------------------------
SELECT c.cust_id, c.name
FROM customer c
LEFT JOIN subscription s ON s.cust_id = c.cust_id
WHERE s.sub_id IS NULL
ORDER BY c.cust_id;

-- ----------------------------------------------------------
-- [과제 3 · C2] 서브쿼리 & 뷰
-- (a) CTE로 헤비유저(가입건별 총 data_mb) 추출 — 평균 초과 사용자
-- ----------------------------------------------------------
WITH sub_usage AS (
  SELECT sub_id, SUM(data_mb) AS total_data_mb
  FROM usage_log
  GROUP BY sub_id
)
SELECT sub_id, total_data_mb
FROM sub_usage
WHERE total_data_mb > (SELECT AVG(total_data_mb) FROM sub_usage)
ORDER BY total_data_mb DESC;

-- (b) 활성가입 상세 뷰 생성 + 조회
CREATE OR REPLACE VIEW active_subscription_detail AS
SELECT s.sub_id, c.cust_id, c.name AS cust_name, p.plan_name, p.monthly_fee, s.start_dt
FROM subscription s
JOIN customer c ON c.cust_id = s.cust_id
JOIN plan p ON p.plan_id = s.plan_id
WHERE s.status = 'ACTIVE';

SELECT * FROM active_subscription_detail ORDER BY start_dt DESC LIMIT 20;

-- ----------------------------------------------------------
-- [과제 4 · C3] 집계 & ROLLUP
-- 요금제별 활성 가입자 수·평균 월요금을 GROUP BY+HAVING, ROLLUP 총계는 COALESCE로 '전체' 라벨
-- ----------------------------------------------------------
SELECT COALESCE(p.plan_name, '전체') AS plan_name,
       COUNT(s.sub_id) AS active_subs,
       ROUND(AVG(p.monthly_fee), 0) AS avg_monthly_fee
FROM subscription s
JOIN plan p ON p.plan_id = s.plan_id
WHERE s.status = 'ACTIVE'
GROUP BY ROLLUP(p.plan_name)
HAVING COUNT(s.sub_id) > 5
ORDER BY plan_name;

-- ----------------------------------------------------------
-- [과제 5 · C3] 윈도우 함수
-- 월별 사용량(usage_log.data_mb)을 CTE로 집계 후 ROW_NUMBER(월별 순위)·
-- LAG(전월 대비 증감)·SUM OVER(누적합)
-- ----------------------------------------------------------
WITH monthly_usage AS (
  SELECT sub_id, DATE_TRUNC('month', use_dt)::date AS usage_month, SUM(data_mb) AS total_data_mb
  FROM usage_log
  GROUP BY sub_id, DATE_TRUNC('month', use_dt)
)
SELECT
  sub_id,
  usage_month,
  total_data_mb,
  ROW_NUMBER() OVER (PARTITION BY usage_month ORDER BY total_data_mb DESC) AS rank_in_month,
  total_data_mb - LAG(total_data_mb) OVER (PARTITION BY sub_id ORDER BY usage_month) AS diff_from_prev_month,
  SUM(total_data_mb) OVER (PARTITION BY sub_id ORDER BY usage_month) AS cumulative_data_mb
FROM monthly_usage
ORDER BY sub_id, usage_month;

-- ==========================================================
-- [과제 6 · C4] 트랜잭션 & ACID  (account 테이블 필요: 03_account.sql 선적재)
-- 한 세션(DBeaver 편집기 1개)에서 순서대로 실행
-- ==========================================================

-- (1) 정상 이체 — 원자성(Atomicity): 두 UPDATE가 한 트랜잭션으로 함께 반영
SELECT acct_id, owner, balance FROM account ORDER BY acct_id;  -- 이체 전 잔액 확인

BEGIN;
UPDATE account SET balance = balance - 30000 WHERE acct_id = 101;
UPDATE account SET balance = balance + 30000 WHERE acct_id = 102;
COMMIT;

SELECT acct_id, owner, balance FROM account WHERE acct_id IN (101,102) ORDER BY acct_id;
-- 101: 100000→70000, 102: 50000→80000 이면 성공

-- (2) CHECK 위반 → 전체 롤백 (103번 계좌는 잔액 0원, 50만원 인출 시도 시 음수가 되어 거부됨)
BEGIN;
UPDATE account SET balance = balance - 500000 WHERE acct_id = 103;
-- ERROR: violates check constraint "account_balance_check" 발생 확인
ROLLBACK;

SELECT acct_id, balance FROM account WHERE acct_id = 103;  -- 0 그대로면 롤백 성공

-- (3) SAVEPOINT로 부분 롤백
BEGIN;
UPDATE account SET balance = balance - 5000 WHERE acct_id = 104;   -- 정상 차감(유지될 부분)
SAVEPOINT sp1;
UPDATE account SET balance = balance - 1000000 WHERE acct_id = 104; -- CHECK 위반(취소될 부분)
-- ERROR 발생 확인 후:
ROLLBACK TO SAVEPOINT sp1;
COMMIT;

SELECT acct_id, balance FROM account WHERE acct_id = 104;  -- 300000-5000=295000 이면 부분 롤백 성공

-- ==========================================================
-- [과제 7 · C4 · 2세션] 동시성 · 격리수준 · 데드락
-- DBeaver 연결을 2개 열어(또는 psql 창 2개) 아래 세션A/세션B를 각 창에 붙여넣고
-- "거의 동시에"(A 먼저 1~2줄 실행 후 B 실행) 순서대로 실행하세요.
-- ==========================================================

-- ---------- (a) 격리수준 비교: READ COMMITTED vs REPEATABLE READ ----------
-- [세션 A - RC] : 아래를 한 줄씩 실행하며 중간에 세션B의 UPDATE+COMMIT을 끼워 넣는다
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT balance FROM account WHERE acct_id = 101;   -- 1차 조회 (예: 70000)
-- << 이 시점에 세션 B에서 UPDATE account SET balance = balance - 1000 WHERE acct_id=101; COMMIT; 실행 >>
SELECT balance FROM account WHERE acct_id = 101;   -- 2차 조회 → RC는 B의 커밋이 "즉시 반영"되어 값이 바뀜
COMMIT;

-- [세션 A - RR] : 위와 동일한 절차를 격리수준만 바꿔서 반복
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM account WHERE acct_id = 101;   -- 1차 조회
-- << 이 시점에 세션 B에서 UPDATE ... COMMIT; 실행 >>
SELECT balance FROM account WHERE acct_id = 101;   -- 2차 조회 → RR은 트랜잭션 시작 시점 스냅샷 유지, 값 그대로
COMMIT;

-- [세션 B] : 위 두 케이스 각각에서 세션A의 "1차 조회" 직후 실행
UPDATE account SET balance = balance - 1000 WHERE acct_id = 101;
COMMIT;

-- ---------- (b) 데드락 재현: 계좌 101·102를 서로 교차 순서로 잠금 ----------
-- [세션 A] 101 → 102 순서로 UPDATE
BEGIN;
UPDATE account SET balance = balance - 1000 WHERE acct_id = 101;  -- 101 잠금
-- (잠시 대기 후 세션 B가 102를 잠글 시간을 준다)
UPDATE account SET balance = balance + 1000 WHERE acct_id = 102;  -- 102 대기 → 데드락 유발
COMMIT;

-- [세션 B] 102 → 101 순서로 UPDATE (세션 A보다 살짝 늦게 시작)
BEGIN;
UPDATE account SET balance = balance - 1000 WHERE acct_id = 102;  -- 102 잠금
UPDATE account SET balance = balance + 1000 WHERE acct_id = 101;  -- 101 대기 → 순환 대기 → PostgreSQL이 둘 중 하나를 강제 종료
COMMIT;
-- 한쪽 세션에 "ERROR: deadlock detected"가 뜨고 해당 트랜잭션은 자동 ROLLBACK됨.
-- 살아남은 세션은 정상 COMMIT됨 → 두 세션 화면을 각각 캡처해 제출.
