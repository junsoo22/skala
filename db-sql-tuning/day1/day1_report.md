# [SKALA 4기] Day1 종합실습 — 개인 과제(B) 제출 문서

> 이 문서는 제출 PDF 초안입니다. `[대괄호]` 표시된 부분을 본인 정보/스크린샷으로 채운 뒤
> Word/Keynote/Pages 등으로 옮기거나, 이 Markdown을 그대로 PDF로 변환해 제출하세요.
> 파일명 규칙: `[반][번호][이름][DAY1][과제명].pdf`

---

## 1. 표지

- 이름: `[이름]`
- 반 / 번호: `[반] / [번호]`
- 과정명: SKALA 4기 — AI 서비스를 위한 SW 기초(Full-stack Engineering)
- 제출일: `[제출일, 예: 2026-07-22]`
- 실습 주제: Day1 — 환경 구축·데이터 모델링·SQL 기초 (telecom 가입자 관리 DB)

---

## 2. 요구사항 요약 — 설계 방향·가정

- **시나리오**: 통신사 가입자 관리 시스템의 DB(telecom)를 설계·구축한다. 고객(customer)·요금제(plan)·가입(subscription)·사용로그(usage_log) 4개 테이블로 구성된다.
- **설계 방향**:
  - `customer`는 고객 1명당 1행(마스터), `plan`은 요금제 1종당 1행(마스터)로 둔다.
  - `subscription`은 고객과 요금제 간 **다대다 이력**을 표현하는 연결 테이블로, 한 고객이 여러 번 가입/해지할 수 있으므로 `cust_id`를 FK로 두되 PK는 별도 서로게이트 키(`sub_id`)로 둔다.
  - `usage_log`는 가입 건별 일별 사용량을 기록하는 트랜잭션성 테이블로, 볼륨이 가장 크므로 인덱스·튜닝은 Day3에서 다룬다.
- **가정**:
  - `end_dt IS NULL`이면 현재 사용 중인 가입으로 간주한다.
  - `region`, `gender`는 필수값이 아닐 수 있어 NULL을 허용한다.
  - `grade`는 기본값 `SILVER`이며 BRONZE/SILVER/GOLD/VIP 4단계로 관리한다.

---

## 3. ERD 이미지

> **[여기에 스크린샷 삽입]**
> DBeaver에서 `telecom → Schemas → public 우클릭 → View Diagram`으로 역공학 ERD를 열어 캡처하세요.
> (교재 LAB4 STEP1, p.30 참고 — telecom 노드가 아니라 **public 스키마**에서 열어야 ERD 탭이 뜹니다.)

**범례**:
- 사각형 = 테이블, 굵은 컬럼 = PK(기본키)
- 선 끝 갈매기(●) = FK를 가진 자식(N) 쪽, 반대편(선만) = 부모(1) 쪽 → **1:N 관계**

**관계 요약** (텍스트 백업 — 이미지 삽입 후에도 유지 권장):

```
customer (1) ──< subscription (N) >── (1) plan
                     │
                     └──< usage_log (N)  [부모: subscription]
```

| 관계 | 부모(1) | 자식(N) | FK 컬럼 |
|---|---|---|---|
| 고객-가입 | customer | subscription | subscription.cust_id → customer.cust_id |
| 요금제-가입 | plan | subscription | subscription.plan_id → plan.plan_id |
| 가입-사용로그 | subscription | usage_log | usage_log.sub_id → subscription.sub_id |

---

## 4. 정규화 워크시트 — 과제 1 (B-1, 20점)

### 대상 비정규화 표 (주문 내역, PK = order_id + prod_id)

| order_id | order_dt | cust_id | cust_name | prod_id | prod_name | unit_price | qty |
|---|---|---|---|---|---|---|---|
| O1001 | 2024-06-01 | C01 | 김하늘 | P10 | 노트북 | 1200000 | 1 |
| O1001 | 2024-06-01 | C01 | 김하늘 | P22 | 마우스 | 25000 | 2 |
| O1002 | 2024-06-03 | C02 | 이준호 | P10 | 노트북 | 1200000 | 1 |

### ① 함수 종속 식별

| 종속 관계 | 의미 |
|---|---|
| `order_id → order_dt, cust_id` | 주문 단위 속성은 주문번호에만 종속 |
| `cust_id → cust_name` | 고객명은 고객번호에 종속(이행 종속) |
| `prod_id → prod_name, unit_price` | 상품 단위 속성은 상품번호에만 종속 |
| `(order_id, prod_id) → qty` | 수량은 "어느 주문의 어느 상품인지"(복합키) 전체에 종속 |

### ② 1NF → 2NF → 3NF 분해

**1NF 확인**: 모든 칸이 원자값이고 반복 그룹이 없으므로 주어진 표는 이미 1NF를 만족한다.

**1NF → 2NF (부분 종속 제거)**
PK가 `(order_id, prod_id)` 복합키인데, `order_dt·cust_id·cust_name`은 `order_id`에만, `prod_name·unit_price`는 `prod_id`에만 종속되는 **부분 종속**이 존재 → 분리한다.

- `ORDERS(order_id PK, order_dt, cust_id, cust_name)`
- `PRODUCTS(prod_id PK, prod_name, unit_price)`
- `ORDER_ITEMS(order_id, prod_id, qty)` — PK(order_id, prod_id)

**2NF → 3NF (이행 종속 제거)**
`ORDERS`에서 `order_id → cust_id → cust_name`으로 **이행 종속**이 존재(키가 아닌 속성이 다른 키가 아닌 속성에 종속) → `cust_name`을 분리한다.

- `CUSTOMERS(cust_id PK, cust_name)`
- `ORDERS(order_id PK, order_dt, cust_id FK → CUSTOMERS)`
- `PRODUCTS(prod_id PK, prod_name, unit_price)` — 상품 속성 간 이행 종속 없음, 그대로 유지
- `ORDER_ITEMS(order_id FK → ORDERS, prod_id FK → PRODUCTS, qty)` — PK(order_id, prod_id)

### ③ 최종 테이블 · PK·FK 정리

| 테이블 | PK | FK |
|---|---|---|
| CUSTOMERS | cust_id | — |
| PRODUCTS | prod_id | — |
| ORDERS | order_id | cust_id → CUSTOMERS.cust_id |
| ORDER_ITEMS | (order_id, prod_id) | order_id → ORDERS.order_id, prod_id → PRODUCTS.prod_id |

### 이상현상(Anomaly) 해소 근거

- **갱신 이상**: 분해 전에는 '노트북' 단가 변경 시 해당 상품이 포함된 모든 주문행을 수정해야 했지만, 분해 후에는 `PRODUCTS` 1행만 수정하면 된다.
- **삽입 이상**: 분해 전에는 주문이 없으면 신규 상품·고객을 등록할 수 없었지만, 분해 후에는 `PRODUCTS`/`CUSTOMERS`에 주문 없이도 독립적으로 등록 가능하다.
- **삭제 이상**: 분해 전에는 마지막 주문행을 삭제하면 상품·고객 정보까지 함께 사라졌지만, 분해 후에는 `ORDER_ITEMS`/`ORDERS` 삭제와 무관하게 `PRODUCTS`/`CUSTOMERS` 정보가 보존된다.

---

## 5. 단일 조회 쿼리 — 과제 2 (B-2, 20점)

**대상 테이블**: `customer` (고객 마스터, public 스키마, LAB3 적재분)

**요구사항 반영**:
1. `WHERE ... IN (...) AND ...` — grade가 GOLD 또는 VIP이고, 2020년 이후 가입한 고객만
2. `AGE(birth_ymd)`로 만 나이 계산
3. `CASE`로 연령대 라벨(30 미만 '청년' / 30~49 '중년' / 50 이상 '장년')
4. `COALESCE(region, '미상')`로 NULL 지역 대체
5. `ORDER BY join_dt ASC LIMIT 15` — 가입일 오래된 순 상위 15건

```sql
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
```

---

## 6. PostgreSQL 접속 결과 화면

> **[여기에 스크린샷 삽입]**
> DBeaver에서 `postgres · localhost:5432` 연결 상태(Connected) 또는
> `SELECT version();` 실행 결과 화면을 캡처하세요.

로컬 환경에서 확인한 버전 (참고용 텍스트):
```
PostgreSQL 17.10 (Homebrew) on aarch64-apple-darwin, ...
```

---

## 7. 문항별 SQL문 + 실행 결과 화면

### 과제 2 실행 결과 (참고용 — 실제 제출 시 본인 DBeaver 화면 재캡처 필요)

> ⚠️ 아래는 로컬 검증용으로 실행한 결과이며, `01_seed_core.sql`이 매 적재 시 `random()`으로
> 데이터를 생성하므로 **본인이 적재한 DB의 실제 값과 다릅니다.** 쿼리 로직 검증용으로만
> 참고하고, 제출용 캡처는 반드시 본인 DBeaver 화면에서 다시 떠야 합니다.

```
 cust_id |  name   | grade | age | age_group | region |  join_dt
---------+---------+-------+-----+-----------+--------+------------
     370 | 고객370 | GOLD  |   8 | 청년      | 인천   | 2022-01-05
     180 | 고객180 | VIP   |  31 | 중년      | 서울   | 2022-01-06
     314 | 고객314 | VIP   |  42 | 중년      | 인천   | 2022-01-08
     428 | 고객428 | VIP   |  54 | 장년      | 대전   | 2022-01-10
     345 | 고객345 | GOLD  |  20 | 청년      | 강원   | 2022-01-16
       ...(총 15건, LIMIT 15로 제한)
```

> **[여기에 DBeaver 실행 화면(쿼리+결과 그리드) 스크린샷 삽입]**
> `queries.sql`의 과제 2 쿼리를 telecom 연결에서 실행한 뒤, SQL 편집기와 결과 그리드가
> 한 화면에 보이도록 캡처하세요 (교재 p.5 "SQL은 텍스트로" 규칙: 쿼리 텍스트도 별도로 붙여넣을 것).
