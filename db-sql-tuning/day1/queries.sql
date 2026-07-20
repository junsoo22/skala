-- ==========================================================
-- Day1 개인 과제 SQL — DBeaver SQL 편집기에 그대로 붙여넣어 실행
-- 대상: telecom DB (public 스키마)
-- ==========================================================

-- ----------------------------------------------------------
-- [과제 1] 정규화 워크시트는 SQL이 아니라 별도 문서(정규화 근거 서술)로 제출.
-- day1_report.md의 "과제 1" 절 참고.
-- ----------------------------------------------------------

-- ----------------------------------------------------------
-- [과제 2 · B-2] 단일 테이블 조회 — customer
-- 요구사항 5가지:
--   1) WHERE(IN·AND) — grade가 GOLD 또는 VIP이고, 2020년 이후 가입한 고객만
--   2) 나이 계산 — birth_ymd로 만 나이 파생(AGE 활용)
--   3) CASE(범위 분기) — 나이로 연령대: 30 미만 '청년' / 30~49 '중년' / 50 이상 '장년'
--   4) COALESCE — region이 NULL이면 '미상'으로 대체
--   5) ORDER BY(ASC) — 가입일(join_dt) 오래된 순, 상위 15건(LIMIT)
-- ----------------------------------------------------------
SELECT
  cust_id,
  name,
  grade,
  EXTRACT(YEAR FROM AGE(birth_ymd)) AS age,
  CASE
    WHEN EXTRACT(YEAR FROM AGE(birth_ymd)) < 30 THEN '청년'
    WHEN EXTRACT(YEAR FROM AGE(birth_ymd)) BETWEEN 30 AND 49 THEN '중년'
    ELSE '장년'
  END AS age_group,
  COALESCE(region, '미상') AS region,
  join_dt
FROM customer
WHERE grade IN ('GOLD', 'VIP')
  AND join_dt >= DATE '2020-01-01'
ORDER BY join_dt ASC
LIMIT 15;

-- ----------------------------------------------------------
-- 접속 확인용 (제출물 "PostgreSQL 접속 결과 화면"에 캡처)
-- ----------------------------------------------------------
SELECT version();
SELECT count(*) FROM customer;   -- 500 이어야 정상 적재
