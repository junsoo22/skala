-- ==========================================================
-- Day3 조별 과제 SQL — DBeaver/DataGrip SQL 편집기에 그대로 붙여넣어 실행
-- 대상: telecom DB (public 스키마) — Day1 산출물 + 02_seed_bulk.sql 대용량 적재 필요
-- 사전 준비: psql -d telecom -f 02_seed_bulk.sql   (Day3 당일에만, usage_log 수십만 행 추가)
-- 출처: [4기] 15_인덱스와쿼리튜닝 교육생배포용 PDF 기준으로 세부 요구사항 재정리
-- ==========================================================

-- ----------------------------------------------------------
-- [사전 준비] 적재 확인
-- ----------------------------------------------------------
SELECT count(*) FROM subscription;   -- Day1 산출물 확인
SELECT count(*) FROM usage_log;      -- 02_seed_bulk.sql 적재 후 수십만 행 나와야 정상
-- ⚠️ 이 시점엔 인덱스를 아직 만들지 않는다 — Before(인덱스 無) 상태를 먼저 측정해야 함


-- ==========================================================
-- [과제 1 · C-5 · 10점] 인덱스 Before/After
-- 시나리오: 특정 가입자·기간 사용량 조회가 느림. 인덱스 유무로 실행시간을 직접 측정.
-- ==========================================================

-- BEFORE — 인덱스 없는 상태
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM usage_log
WHERE sub_id = 243 AND use_dt >= '2026-01-01';

-- 복합 인덱스 생성 (등치 컬럼 sub_id를 앞, 범위 컬럼 use_dt를 뒤)
CREATE INDEX idx_ul_sub_used ON usage_log (sub_id, use_dt);

-- AFTER — 인덱스 생성 후 (동일 쿼리, Seq→Index 비교)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM usage_log
WHERE sub_id = 243 AND use_dt >= '2026-01-01';

-- 커버링 인덱스로 교체 — Index-Only Scan 유도
-- 대량 적재 직후엔 먼저 VACUUM 필요 (Heap Fetches 0을 위해)
VACUUM usage_log;

DROP INDEX idx_ul_sub_used;
CREATE INDEX idx_ul_sub_used ON usage_log (sub_id, use_dt) INCLUDE (data_mb);

EXPLAIN (ANALYZE, BUFFERS)
SELECT use_dt, data_mb FROM usage_log   -- SELECT * 대신 필요한 컬럼만
WHERE sub_id = 243 AND use_dt >= '2026-01-01';


-- ==========================================================
-- [과제 2 · C-5 · 10점] EXPLAIN 병목 진단
-- 시나리오: 월별 사용량 집계 리포트가 느림. 추측하지 말고 측정.
-- ==========================================================

-- 진단 대상 — 느린 쿼리 (EXTRACT가 use_dt를 함수로 감싸 SARGable 위반)
EXPLAIN (ANALYZE, BUFFERS)
SELECT to_char(use_dt,'YYYY-MM') ym, SUM(data_mb)
FROM usage_log
WHERE EXTRACT(year FROM use_dt) = 2026
GROUP BY 1 ORDER BY 1;

-- 통계 갱신 후 재측정 (인덱스 없이 통계만으로 개선되는지 관찰 — estimated rows는 안 바뀌는 게 정상)
ANALYZE usage_log;

EXPLAIN (ANALYZE, BUFFERS)
SELECT to_char(use_dt,'YYYY-MM') ym, SUM(data_mb)
FROM usage_log
WHERE EXTRACT(year FROM use_dt) = 2026
GROUP BY 1 ORDER BY 1;
-- 결론: estimated rows가 ANALYZE 전후로 안 바뀜 → 통계 문제가 아니라 SARGable 위반(구조적 문제)
--       → 쿼리 리라이팅(과제3 ①)이 필요함을 증명


-- ==========================================================
-- [과제 3 · C-6 · 10점] 쿼리 리라이팅
-- 과제 개요: 인덱스를 못 타는 쿼리 4종을 SARGable·키셋 형태로 고쳐 쓰고,
-- 변경마다 EXPLAIN으로 Seq→Index 변화를 확인. 데이터는 과제1의 usage_log 그대로 사용.
-- ==========================================================

-- ---------- 사전 준비 ----------
SELECT count(*) FROM usage_log;   -- 재적재 불필요, 과제1 데이터 그대로

-- 과제1 복합 인덱스 존재만 확인 (재생성 아님)
SELECT indexname FROM pg_indexes WHERE tablename = 'usage_log';

-- 과제3 전용 인덱스 2개 신규 생성
-- LIKE 앞고정용 — telecom DB가 C 로케일이 아니므로 pattern_ops 필수(없으면 prefix LIKE도 인덱스 못 탐)
CREATE INDEX IF NOT EXISTS idx_cust_name ON customer (name varchar_pattern_ops);
-- use_dt 함수제거·키셋 페이지네이션용
CREATE INDEX IF NOT EXISTS idx_ul_used ON usage_log (use_dt, usage_id);

ANALYZE usage_log;
ANALYZE customer;

-- ---------- ① 함수 제거 (컬럼 가공 제거) — FROM usage_log ----------
-- Before (함수로 감쌈 — Seq Scan)
-- 주의: date(use_dt)는 use_dt가 이미 DATE 타입이라 PostgreSQL이 자동 최적화해버려
--       안티패턴이 재현 안 됨 → to_char로 진짜 함수 래핑을 강제함
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM usage_log
WHERE to_char(use_dt,'YYYY-MM-DD') = '2026-01-03';

-- After (범위 조건으로 전환 — Index Scan)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM usage_log
WHERE use_dt >= '2026-01-03' AND use_dt < '2026-01-04';

-- ---------- ② LIKE 앞고정 — FROM customer ----------
-- Before (앞 와일드카드 — 인덱스 못 탐)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM customer
WHERE name LIKE '%kim';

-- After (가능하면 앞고정으로 변환)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM customer
WHERE name LIKE 'kim%';

-- ---------- ③ 키셋(Keyset) 페이지네이션 — FROM usage_log ----------
-- Before (큰 OFFSET)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM usage_log
ORDER BY use_dt DESC, usage_id DESC
LIMIT 20 OFFSET 100000;

-- After (직전 페이지 마지막 값부터 — usage_id는 PK, 동점 정렬용 tiebreaker)
-- 가장 중요: Before의 OFFSET 100000이 가리키는 같은 페이지를 보려면
-- 경계값을 반드시 OFFSET 99999(=100000번째 행)에서 구해야 함(19가 아님!):
SELECT use_dt, usage_id FROM usage_log ORDER BY use_dt DESC, usage_id DESC LIMIT 1 OFFSET 99999;
-- 아래 값은 예시 — 팀 DB에서 위 쿼리로 재조회한 값으로 교체할 것
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM usage_log
WHERE (use_dt, usage_id) < ('2026-07-27', 839829)
ORDER BY use_dt DESC, usage_id DESC
LIMIT 20;

-- ---------- ④ 상관 서브쿼리 → JOIN 재작성 ----------
-- Before (상관 서브쿼리)
EXPLAIN (ANALYZE, BUFFERS)
SELECT s.sub_id, (SELECT SUM(u.data_mb) FROM usage_log u WHERE u.sub_id = s.sub_id) AS total_mb
FROM subscription s;

-- After (LEFT JOIN + GROUP BY로 한 번에 집계 — INNER JOIN이 아니라 LEFT JOIN이어야 함)
-- 주의: INNER JOIN을 쓰면 사용로그가 전혀 없는 구독이 통째로 빠져 결과 행 수가 달라짐(800→600행 오류)
EXPLAIN (ANALYZE, BUFFERS)
SELECT s.sub_id, SUM(u.data_mb) AS total_mb
FROM subscription s
LEFT JOIN usage_log u ON u.sub_id = s.sub_id
GROUP BY s.sub_id;


-- ==========================================================
-- [과제 4 · C-7 · 조별 40점] 종합 튜닝
-- 시나리오: 가입자별 연간 사용량 리포트 쿼리가 느림. 5단계 파이프라인으로 개선.
-- 힌트: 한 번에 다 바꾸지 말고 한 가지씩 적용·측정해 효과를 분리해서 본다.
-- ==========================================================

-- 주어진 느린 쿼리
-- 1단계 · 진단
EXPLAIN (ANALYZE, BUFFERS)
SELECT sub_id, SUM(data_mb) AS total_mb
FROM usage_log
WHERE EXTRACT(YEAR FROM use_dt) = 2026
GROUP BY sub_id
ORDER BY total_mb DESC;

-- 2단계 · 인덱스 확인 (신규 생성 불필요 — 과제3에서 만든 idx_ul_sub_used·idx_ul_used 재사용)
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'usage_log';

-- 3단계 · 리라이팅 (SARGable·불필요 연산 제거 — EXTRACT → 범위 조건)
EXPLAIN (ANALYZE, BUFFERS)
SELECT sub_id, SUM(data_mb) AS total_mb
FROM usage_log
WHERE use_dt >= '2026-01-01' AND use_dt < '2027-01-01'
GROUP BY sub_id
ORDER BY total_mb DESC;

-- 4단계(측정)·5단계(설명)는 위 1단계·3단계 EXPLAIN 결과를 Before/After 비교표로 정리해 문서화
-- 관찰 포인트: 선택도가 높아 Seq Scan은 그대로지만(정상), estimated rows가 정확해지며
-- Sort+GroupAggregate(디스크 스필 가능)에서 HashAggregate(메모리)로 집계 전략이 바뀜
