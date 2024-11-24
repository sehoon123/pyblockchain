# NFT 블록체인 API와 P2P 네트워크

이 프로젝트는 NFT(Non-Fungible Token)를 관리할 수 있는 간단한 블록체인 API를 구현하며, P2P 네트워크 기능을 포함합니다. 블록체인은 채굴, 블록 및 트랜잭션 브로드캐스트, 노드 간 체인 동기화를 지원합니다.

## 주요 기능

- **블록체인 기능**:
  - NFT 생성 및 트랜잭션 관리
  - 작업 증명을 통한 블록 채굴
  - 블록체인 유효성 검증
  - 블록체인 데이터 영구 저장

- **P2P 네트워크**:
  - 네트워크에 노드 등록
  - 블록 및 트랜잭션 브로드캐스트
  - 네트워크 노드 간 체인 동기화

- **API 엔드포인트**:
  - 트랜잭션 생성 및 브로드캐스트
  - 블록 채굴 및 브로드캐스트
  - 새로운 노드 등록
  - 체인 동기화 (수동 및 자동 지원)

## 사전 요구 사항

- Python 3.9 이상
- 가상환경 (권장)

## 설치 방법

1. 레포지토리 클론:

   ```bash
   git clone https://github.com/sehoon123/pyblockchain.git
   cd pyblockchain
   ```

2. 가상환경 생성:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows에서는 `venv\Scripts\activate`
   ```

3. 종속성 설치:

   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 파일 생성:
   
   ```bash
   echo 'AWS_REGION="your-region"' >> .env
   echo 'AWS_ACCESS_KEY_ID="your-access-key"' >> .env
   echo 'AWS_SECRET_ACCESS_KEY="your-secret-key"' >> .env
   echo 'S3_BUCKET_NAME="your-s3-bucket-name"' >> .env

   ```

5. 서버 실행:

   ```bash
   uvicorn main:app --reload --port 8000
   ```

   추가 노드를 실행하려면 다른 포트를 사용하세요:

   ```bash
   uvicorn main:app --reload --port 8001
   ```

## 디렉터리 구조

```
.
├── blockchain.py            # 블록체인 및 P2P 로직
├── blockchain_route.py      # 블록체인 작업을 위한 FastAPI 라우트
├── main.py                  # FastAPI 진입점
├── models.py                # 데이터 검증을 위한 Pydantic 모델
├── requirements.txt         # Python 종속성 목록
└── README.md                # 프로젝트 문서
```

## API 엔드포인트 목록

### 블록체인 작업

| **엔드포인트**                | **HTTP 메서드** | **설명**                                   |
|-----------------------------|----------------|------------------------------------------|
| `/api/create_transaction`  | POST           | 새로운 NFT 트랜잭션 생성 및 추가              |
| `/api/mine_block`          | POST           | 새로운 블록을 채굴 및 체인에 추가             |
| `/api/blockchain`          | GET            | 전체 블록체인 데이터 조회                   |
| `/api/validate`            | GET            | 현재 블록체인의 무결성 검증                 |
| `/api/previous_block`      | GET            | 가장 최근의 블록 데이터 조회                 |
| `/api/nfts`                | GET            | 블록체인에 저장된 모든 NFT 조회               |
| `/api/nft/{dna}`           | GET            | 특정 DNA를 가진 NFT와 소유자 정보 조회         |
| `/api/transactions`        | GET            | 블록체인의 모든 트랜잭션 조회                |
| `/api/block`               | GET            | 특정 인덱스 또는 해시값을 가진 블록 조회        |


### P2P 네트워크

| **엔드포인트**                | **HTTP 메서드** | **설명**                                   |
|-----------------------------|----------------|------------------------------------------|
| `/api/register_node`        | POST           | 새로운 노드를 네트워크에 등록                |
| `/api/replace_chain`        | GET            | 네트워크의 다른 노드와 비교해 체인 동기화         |
| `/api/broadcast_transaction` | POST          | 트랜잭션을 다른 네트워크 노드로 브로드캐스트      |
| `/api/broadcast_block`      | POST           | 블록을 네트워크의 다른 노드로 브로드캐스트       |
| `/api/receive_block`        | POST           | 다른 노드로부터 블록을 수신해 체인에 추가         |


### 기타 유틸리티

| **엔드포인트**                | **HTTP 메서드** | **설명**                                   |
|-----------------------------|----------------|------------------------------------------|
| `/api/generate_presigned_url` | GET          | S3 업로드를 위한 Pre-signed URL 생성        |

## 사용 방법

### 1. 노드 실행

서버를 여러 포트에서 실행하여 네트워크를 구성합니다.

```bash
# 첫 번째 노드를 포트 8000에서 실행
uvicorn main:app --reload --port 8000

# 두 번째 노드를 포트 8001에서 실행
uvicorn main:app --reload --port 8001
```

### 2. 노드 등록

노드끼리 서로를 등록하여 네트워크를 만듭니다.

```bash
# 노드 A (http://localhost:8000) 에서 노드 B 등록
curl -X 'POST' \
  'http://localhost:8000/api/register_node' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "node_address": "http://localhost:8001"
}'

# 노드 B (http://localhost:8001) 에서 노드 A 등록
curl -X 'POST' \
  'http://localhost:8001/api/register_node' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "node_address": "http://localhost:8000"
}'
```


### 3. 트랜잭션 생성

트랜잭션을 생성하고 네트워크의 모든 노드로 브로드캐스트합니다.
초기에 주인이 없는 NFT는 sender 필드에 "SYSTEM"을 사용합니다.
이후 NFT를 소유한 주인은 sender 필드에 자신의 이름을 사용합니다.

```bash
curl -X 'POST' \
  'http://localhost:8001/api/create_transaction' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "sender": "SYSTEM",
  "receiver": "KKKK111K",
  "nft": {
    "name": "KKK111KK",
    "description": "string",
    "image": "string",
    "dna": "KKKK111KKKK",
    "edition": 0,
    "date": 0,
    "attributes": [
      {
        "trait_type": "string",
        "value": "string"
      }
    ],
    "compiler": "string"
  },
  "price": 0,
  "timestamp": "string"
}'
```

### 4. 블록 채굴

노드에서 블록을 채굴하고 네트워크의 다른 노드로 브로드캐스트합니다.

```bash
curl -X 'POST' \
  'http://localhost:8001/api/mine_block' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "miner_address": "localhost:8001"
}'
```

### 5. 체인 동기화

각 노드는 백그라운드에서 체인을 자동으로 동기화합니다. 하지만 필요 시 수동으로 호출할 수도 있습니다.

```bash
curl -X GET "http://localhost:8000/api/replace_chain"
```

## 전체 흐름 예제

1. **노드 A (http://localhost:8000)와 노드 B (http://localhost:8001) 실행**
   
   ```bash
   # 노드 A 실행
   uvicorn main:app --reload --port 8000
   
   # 노드 B 실행
   uvicorn main:app --reload --port 8001
   ```

2. **노드 간 등록**
   
   ```bash
   # 노드 A (http://localhost:8000) 에서 노드 B 등록
   curl -X 'POST' \
   'http://localhost:8000/api/register_node' \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "node_address": "http://localhost:8001"
   }'

   # 노드 B (http://localhost:8001) 에서 노드 A 등록
   curl -X 'POST' \
   'http://localhost:8001/api/register_node' \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "node_address": "http://localhost:8000"
   }'
   ```

3. **트랜잭션 생성 및 브로드캐스트**
   
   ```bash
   curl -X 'POST' \
   'http://localhost:8001/api/create_transaction' \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "sender": "SYSTEM",
   "receiver": "KKKK111K",
   "nft": {
      "name": "KKK111KK",
      "description": "string",
      "image": "string",
      "dna": "KKKK111KKKK",
      "edition": 0,
      "date": 0,
      "attributes": [
         {
         "trait_type": "string",
         "value": "string"
         }
      ],
      "compiler": "string"
   },
   "price": 0,
   "timestamp": "string"
   }'
    ```

4. **블록 채굴 및 브로드캐스트**
   miner1이 채굴을 시작하고 성공하면 블록을 브로드캐스트합니다.
   ```bash
   curl -X 'POST' \ 'http://localhost:8001/api/mine_block' \
   -H 'accept: application/json' \
   -H 'Content-Type: application/json' \
   -d '{
   "miner_address": "localhost:8001"
   }'
   ```

5. **체인 동기화 자동화**
   
   - 노드 A와 노드 B는 백그라운드 작업으로 60초마다 체인을 동기화합니다.

## 개선 방향

- **보안 강화**: 인증 및 암호화를 추가하여 악성 노드를 방지
- **합의 알고리즘 개선**: 간단한 체인 길이 비교 대신 Proof of Stake와 같은 합의 알고리즘 도입
- **네트워크 최적화**: Gossip 프로토콜 등을 사용해 효율적인 데이터 전파 구현
- **에러 처리**: 네트워크 단절 또는 노드 비활성화에 대한 복원력 강화
