-- ==========================================================
-- Day2 조별 과제 SQL — DBeaver SQL 편집기에 그대로 붙여넣어 실행
-- 대상: telecom DB (public 스키마) — Day1 산출물 + 03_account.sql 추가 적재 필요
-- 사전 준비: psql -d telecom -f 03_account.sql   (과제6·7 전에 1회)
-- 출처: [4기] 14_JOIN집계트랜잭션 교육생배포용 PDF 기준으로 세부 요구사항 재정리
-- ==========================================================

-- ----------------------------------------------------------
-- [과제 1 · C-1] 다중 JOIN
-- ① subscription⋈customer⋈plan 3테이블 조인, 활성(ACTIVE) 가입 고객명·요금제명·월요금을
--    월요금 내림차순으로 조회
-- ② 위 결과를 region별로 집계 → 지역별 활성 가입 수(COUNT)와 평균 월요금(AVG)
-- ----------------------------------------------------------

-- ① 다중 JOIN
SELECT c.name AS cust_name, p.plan_name, p.monthly_fee
FROM subscription s
JOIN customer c ON c.cust_id = s.cust_id
JOIN plan p ON p.plan_id = s.plan_id
WHERE s.status = 'ACTIVE'
ORDER BY p.monthly_fee DESC;

-- ② region별 집계
SELECT c.region,
       COUNT(*) AS active_sub_count,
       ROUND(AVG(p.monthly_fee), 0) AS avg_monthly_fee
FROM subscription s
JOIN customer c ON c.cust_id = s.cust_id
JOIN plan p ON p.plan_id = s.plan_id
WHERE s.status = 'ACTIVE'
GROUP BY c.region
ORDER BY c.region;

-- ----------------------------------------------------------
-- [과제 2 · C-2] OUTER JOIN
-- ① 가입 이력이 한 번도 없는 고객을 LEFT JOIN + 자식 PK IS NULL로 찾기
-- ② 활성 가입자가 한 명도 없는 요금제 찾기 (LEFT JOIN + IS NULL 방식)
-- ----------------------------------------------------------

-- ① 가입 이력 없는 고객
SELECT c.cust_id, c.name
FROM customer c
LEFT JOIN subscription s ON s.cust_id = c.cust_id
WHERE s.sub_id IS NULL
ORDER BY c.cust_id;

-- ② 활성 가입자 0명인 요금제 (LEFT JOIN 조건에 status를 넣어야 함 — WHERE에 넣으면 INNER로 변질됨)
SELECT p.plan_id, p.plan_name
FROM plan p
LEFT JOIN subscription s ON s.plan_id = p.plan_id AND s.status = 'ACTIVE'
WHERE s.sub_id IS NULL
ORDER BY p.plan_id;
-- 본 데이터셋 결과 0건 — 10개 요금제 모두 활성 가입자가 1명 이상 있다는 뜻(정상 결과, 오류 아님)

-- ----------------------------------------------------------
-- [과제 3 · C-2] 서브쿼리 & 뷰
-- ① CTE로 헤비유저(가입건별 총 data_mb) 추출 — 전체 평균보다 큰 사용자
-- ② CREATE VIEW v_active_sub — 활성(status='ACTIVE') 가입 상세(name·plan_name·monthly_fee)
-- ③ EXISTS로 가입 이력이 있는 고객만 조회
-- ----------------------------------------------------------

-- ① 헤비유저
WITH sub_usage AS (
  SELECT sub_id, SUM(data_mb) AS tot
  FROM usage_log
  GROUP BY sub_id
)
SELECT sub_id, tot
FROM sub_usage
WHERE tot > (SELECT AVG(tot) FROM sub_usage)
ORDER BY tot DESC;

-- ② 활성가입 상세 뷰
CREATE OR REPLACE VIEW v_active_sub AS
SELECT c.name, p.plan_name, p.monthly_fee
FROM subscription s
JOIN customer c ON c.cust_id = s.cust_id
JOIN plan p ON p.plan_id = s.plan_id
WHERE s.status = 'ACTIVE';

SELECT * FROM v_active_sub LIMIT 20;

-- ③ EXISTS로 가입 이력이 있는 고객만 조회
SELECT c.cust_id, c.name
FROM customer c
WHERE EXISTS (SELECT 1 FROM subscription s WHERE s.cust_id = c.cust_id)
ORDER BY c.cust_id;

-- ----------------------------------------------------------
-- [과제 4 · C-3] 집계 & ROLLUP
-- 요금제별 활성 가입자 수·평균 월요금을 집계 → HAVING으로 가입자 2명 이상만 →
-- GROUP BY ROLLUP(plan_id)로 총계 행 추가 → COALESCE(plan_id::text,'전체')로 라벨링
-- ----------------------------------------------------------
SELECT
  CASE WHEN GROUPING(p.plan_id) = 1 THEN '전체' ELSE p.plan_id::text END AS plan_id,
  CASE WHEN GROUPING(p.plan_id) = 1 THEN '전체' ELSE MAX(p.plan_name) END AS plan_name,
  COUNT(*) AS active_subs,
  ROUND(AVG(p.monthly_fee), 0) AS avg_monthly_fee
FROM subscription s
JOIN plan p ON p.plan_id = s.plan_id
WHERE s.status = 'ACTIVE'
GROUP BY ROLLUP(p.plan_id)
HAVING COUNT(*) >= 2
ORDER BY p.plan_id;

-- ----------------------------------------------------------
-- [과제 5 · C-3] 윈도우 함수
-- 월별 사용량(usage_log.data_mb)을 CTE로 집계 후
-- ROW_NUMBER(월별 순위)·LAG(전월 대비 증감)·SUM OVER(누적합) +
-- RANK / DENSE_RANK 동점 처리 차이 비교
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

-- RANK vs DENSE_RANK 동점 처리 차이 — 1000단위로 반올림해 동점을 인위적으로 만들어 비교
WITH monthly_usage_rounded AS (
  SELECT sub_id, DATE_TRUNC('month', use_dt)::date AS usage_month,
         ROUND(SUM(data_mb), -3) AS mb_rounded
  FROM usage_log
  GROUP BY sub_id, DATE_TRUNC('month', use_dt)
)
SELECT sub_id, usage_month, mb_rounded,
  RANK()       OVER (PARTITION BY usage_month ORDER BY mb_rounded DESC) AS rnk,
  DENSE_RANK() OVER (PARTITION BY usage_month ORDER BY mb_rounded DESC) AS dense_rnk
FROM monthly_usage_rounded
WHERE usage_month = DATE '2024-08-01'
ORDER BY mb_rounded DESC
LIMIT 8;

-- ==========================================================
-- [과제 6 · C-4] 트랜잭션 & ACID  (account 테이블 필요: 03_account.sql 선적재)
-- ⚠️ DBeaver에서 시작 전 Auto Commit 해제 필수 (상단 Auto ▼ → Manual Commit)
-- 한 세션(DBeaver 편집기 1개)에서 문장 단위(⌘Enter)로 순서대로 실행
-- ==========================================================

-- (1) 정상 이체 — 원자성(Atomicity): 101→102 30,000원, 두 UPDATE가 함께 반영
SELECT acct_id, owner, balance FROM account ORDER BY acct_id;  -- 이체 전 잔액 확인

BEGIN;
UPDATE account SET balance = balance - 30000 WHERE acct_id = 101;
UPDATE account SET balance = balance + 30000 WHERE acct_id = 102;
COMMIT;

SELECT acct_id, owner, balance FROM account WHERE acct_id IN (101,102) ORDER BY acct_id;
-- 101: 100000→70000, 102: 50000→80000 이면 성공

-- (2) SAVEPOINT로 부분 롤백 — 정상 출금 후 실수로 과도 출금 → 실수만 취소
BEGIN;
UPDATE account SET balance = balance - 5000 WHERE acct_id = 104;   -- 정상 차감(유지될 부분)
SAVEPOINT sp1;
UPDATE account SET balance = balance - 1000000 WHERE acct_id = 104; -- 실수로 과도 출금(CHECK 위반, 취소될 부분)
-- ERROR 발생 확인 후:
ROLLBACK TO SAVEPOINT sp1;
COMMIT;

SELECT acct_id, balance FROM account WHERE acct_id = 104;  -- 300000-5000=295000 이면 부분 롤백 성공

-- (3) 잔액 부족 이체 → CHECK 위반 → 전체 롤백 (103번 계좌는 잔액 0원)
BEGIN;
UPDATE account SET balance = balance - 500000 WHERE acct_id = 103;
-- ERROR: violates check constraint "account_balance_check" 발생 확인
ROLLBACK;

SELECT acct_id, balance FROM account WHERE acct_id = 103;  -- 0 그대로면 롤백 성공

-- ==========================================================
-- [과제 7 · C-4 · 2세션] 동시성 · 격리수준 · 데드락
-- 시작 전 Auto Commit 해제(수동 커밋) 필수 — 안 끄면 락이 바로 풀려 차이가 재현 안 됨
-- DBeaver 연결을 2개 열어(또는 psql 창 2개) 세션A/세션B로 나누고
-- "문장 단위로 번갈아" 순서대로 실행하세요.
-- ==========================================================

-- ---------- ① lost update 재현 ----------
-- [세션 A]
BEGIN;
SELECT balance FROM account WHERE acct_id = 101;   -- 100000 조회(각자 이 값을 애플리케이션에서 들고 있다고 가정)
-- << 이 시점에 세션 B도 아래 SELECT까지 실행해 같은 100000을 읽게 한다 >>
UPDATE account SET balance = 90000 WHERE acct_id = 101;  -- 자신이 읽은 값 기준 절대값으로 덮어씀
COMMIT;

-- [세션 B] (세션 A의 SELECT 직후, A의 UPDATE보다 먼저 자신의 SELECT까지 실행)
BEGIN;
SELECT balance FROM account WHERE acct_id = 101;   -- A와 동일하게 100000 조회
-- << 세션 A가 COMMIT 완료할 때까지 기다렸다가 아래 실행 >>
UPDATE account SET balance = 80000 WHERE acct_id = 101;  -- A의 -10000 변경을 인지하지 못한 채 덮어씀
COMMIT;
-- 결과: 최종 잔액 80000 — A의 변경(90000)이 사라짐 = lost update

-- ---------- ② 격리수준 비교: READ COMMITTED vs REPEATABLE READ ----------
-- [세션 A - RC]
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT balance FROM account WHERE acct_id = 102;   -- 1차 조회
-- << 이 시점에 세션 B에서 UPDATE account SET balance = balance + 10000 WHERE acct_id=102; COMMIT; 실행 >>
SELECT balance FROM account WHERE acct_id = 102;   -- 2차 조회 → RC는 B의 커밋이 즉시 반영되어 값이 바뀜
COMMIT;

-- [세션 A - RR] (같은 절차를 격리수준만 바꿔 반복)
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM account WHERE acct_id = 102;   -- 1차 조회
-- << 세션 B에서 다시 UPDATE ... COMMIT; 실행 >>
SELECT balance FROM account WHERE acct_id = 102;   -- 2차 조회 → RR은 트랜잭션 시작 시점 스냅샷 유지, 값 그대로
COMMIT;

-- [세션 B] : 위 두 케이스 각각에서 세션A의 "1차 조회" 직후 실행
BEGIN;
UPDATE account SET balance = balance + 10000 WHERE acct_id = 102;
COMMIT;

-- ---------- ③ 데드락 재현: 계좌 101·102를 서로 교차 순서로 잠금 ----------
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

-- ---------- ④ FOR UPDATE로 lost update 방지 ----------
-- [세션 A]
BEGIN;
SELECT balance FROM account WHERE acct_id = 101 FOR UPDATE;  -- 행 락을 선점(다른 세션이 같은 행에 FOR UPDATE 못 함)
-- << 세션 B도 아래 SELECT ... FOR UPDATE를 실행해보게 한다 — A가 커밋할 때까지 대기(멈춤)해야 정상 >>
UPDATE account SET balance = balance - 10000 WHERE acct_id = 101;
COMMIT;  -- 커밋 순간 B의 대기가 풀리며 B가 락을 획득

-- [세션 B] (세션 A의 SELECT FOR UPDATE 직후 실행 — A가 COMMIT 전까지 응답 없이 대기해야 정상)
BEGIN;
SELECT balance FROM account WHERE acct_id = 101 FOR UPDATE;  -- A 커밋 전까지 대기(잠김) 상태 캡처
-- A가 커밋하면 이어서 실행됨 → 이때 balance는 A가 갱신한 값(90000)으로 이미 반영되어 있음
UPDATE account SET balance = balance - 20000 WHERE acct_id = 101;
COMMIT;
-- 결과: 최종 잔액 = 100000-10000-20000 = 70000 (①의 lost update와 달리 두 변경 모두 반영됨)
