아래는 위 내용을 한국어로 번역한 `README.md`입니다.

```markdown
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

4. 서버 실행:

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

## API 엔드포인트

### 블록체인 작업

| 엔드포인트                   | 메서드 | 설명                                     |
|-----------------------------|--------|------------------------------------------|
| `/api/create_transaction`  | POST   | 새로운 트랜잭션 생성                      |
| `/api/mine_block`          | POST   | 새로운 블록 채굴                          |
| `/api/blockchain`          | GET    | 현재 블록체인 조회                        |
| `/api/validate`            | GET    | 현재 블록체인 유효성 검증                 |
| `/api/replace_chain`       | GET    | 네트워크에서 가장 긴 체인으로 교체         |

### P2P 네트워크

| 엔드포인트                   | 메서드 | 설명                                     |
|-----------------------------|--------|------------------------------------------|
| `/api/register_node`       | POST   | 네트워크에 새로운 노드 등록               |
| `/api/broadcast_transaction` | POST | 트랜잭션을 모든 노드에 브로드캐스트         |
| `/api/broadcast_block`     | POST   | 블록을 모든 노드에 브로드캐스트            |
| `/api/receive_block`       | POST   | 다른 노드로부터 블록을 수신하고 검증        |

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
curl -X POST "http://localhost:8000/api/register_node?node_address=http://localhost:8001"

# 노드 B (http://localhost:8001) 에서 노드 A 등록
curl -X POST "http://localhost:8001/api/register_node?node_address=http://localhost:8000"


### 3. 트랜잭션 생성

트랜잭션을 생성하고 네트워크의 모든 노드로 브로드캐스트합니다.
초기에 주인이 없는 NFT는 sender 필드에 "SYSTEM"을 사용합니다.
이후 NFT를 소유한 주인은 sender 필드에 자신의 이름을 사용합니다.

```bash
curl -X POST "http://localhost:8000/api/broadcast_transaction" \
     -H "Content-Type: application/json" \
     -d '{
           "sender": "SYSTEM",
           "receiver": "Amy",
           "nft": {
               "name": "Unique NFT1",
               "description": "A unique digital asset",
               "image": "http://example.com/image.png",
               "dna": "unique-dna-111",
               "edition": 1,
               "date": 20241124,
               "attributes": [{"trait_type": "color", "value": "blue"}],
               "compiler": "solidity"
           },
           "price": 100.0,
           "timestamp": "2024-11-24T14:30:00"
         }'
```

```bash
curl -X POST "http://localhost:8001/api/broadcast_transaction" \
     -H "Content-Type: application/json" \
     -d '{
           "sender": "SYSTEM",
           "receiver": "Bob",
           "nft": {
               "name": "Unique NFT2",
               "description": "A unique digital asset",
               "image": "http://example.com/image.png",
               "dna": "unique-dna-222",
               "edition": 1,
               "date": 20241124,
               "attributes": [{"trait_type": "color", "value": "red"}],
               "compiler": "solidity"
           },
           "price": 100.0,
           "timestamp": "2024-11-24T14:30:00"
         }'
```
### 4. 블록 채굴

노드에서 블록을 채굴하고 네트워크의 다른 노드로 브로드캐스트합니다.

```bash
curl -X POST "http://localhost:8000/api/mine_block?miner_address=miner1"
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
   curl -X POST "http://localhost:8000/api/register_node?node_address=http://localhost:8001"
   ```

3. **트랜잭션 생성 및 브로드캐스트**
   
   ```bash
   curl -X POST "http://localhost:8000/api/broadcast_transaction" \
        -H "Content-Type: application/json" \
        -d '{
              "sender": "SYSTEM",
              "receiver": "Bob",
              "nft": {
                  "name": "Unique NFT",
                  "description": "A unique digital asset",
                  "image": "http://example.com/image.png",
                  "dna": "unique-dna-123",
                  "edition": 1,
                  "date": 20241124,
                  "attributes": [{"trait_type": "color", "value": "blue"}],
                  "compiler": "solidity"
              },
              "price": 100.0,
              "timestamp": "2024-11-24T14:30:00"
            }'
   ```

4. **블록 채굴 및 브로드캐스트**
   
   ```bash
   curl -X POST "http://localhost:8000/api/mine_block?miner_address=miner1"
   ```

5. **체인 동기화 자동화**
   
   - 노드 A와 노드 B는 백그라운드 작업으로 60초마다 체인을 동기화합니다.

## 개선 방향

- **보안 강화**: 인증 및 암호화를 추가하여 악성 노드를 방지
- **합의 알고리즘 개선**: 간단한 체인 길이 비교 대신 Proof of Stake와 같은 합의 알고리즘 도입
- **네트워크 최적화**: Gossip 프로토콜 등을 사용해 효율적인 데이터 전파 구현
- **에러 처리**: 네트워크 단절 또는 노드 비활성화에 대한 복원력 강화
