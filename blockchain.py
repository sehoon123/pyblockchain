# blockchain.py
import datetime as _dt
import hashlib as _hashlib
import json as _json
from typing import List, Optional

class NFT:
    def __init__(
        self,
        name: str,
        description: str,
        image: str,
        dna: str,
        edition: int,
        date: int,
        attributes: list,
        compiler: str,
    ) -> None:
        self.name = name
        self.description = description
        self.image = image
        self.dna = dna
        self.edition = edition
        self.date = date
        self.attributes = attributes
        self.compiler = compiler

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "image": self.image,
            "dna": self.dna,
            "edition": self.edition,
            "date": self.date,
            "attributes": self.attributes,
            "compiler": self.compiler,
        }

    @staticmethod
    def from_dict(data: dict):
        return NFT(
            name=data['name'],
            description=data['description'],
            image=data['image'],
            dna=data['dna'],
            edition=data['edition'],
            date=data['date'],
            attributes=data['attributes'],
            compiler=data['compiler'],
        )

    def __str__(self) -> str:
        return _json.dumps(self.to_dict(), sort_keys=True)


class Transaction:
    def __init__(
        self,
        sender: str,
        receiver: str,
        nft: Optional[NFT],
        price: float,
        timestamp: Optional[str] = None,
    ) -> None:
        self.sender = sender
        self.receiver = receiver
        self.nft = nft
        self.price = price
        self.timestamp = timestamp or str(_dt.datetime.now())

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "nft": self.nft.to_dict() if self.nft else None,
            "price": self.price,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict):
        nft = NFT.from_dict(data['nft']) if data['nft'] else None
        return Transaction(
            sender=data['sender'],
            receiver=data['receiver'],
            nft=nft,
            price=data['price'],
            timestamp=data['timestamp'],
        )

    def __str__(self) -> str:
        return _json.dumps(self.to_dict(), sort_keys=True)


class Blockchain:
    def __init__(self) -> None:
        self.chain: List[dict] = []
        self.pending_transactions: List[Transaction] = []
        self.chain_file = 'blockchain.json'

        # 블록체인 로드 시도
        if not self.load_from_file():
            # 로드 실패 시, 제네시스 블록 생성
            genesis_block = self._create_block(
                proof=1,
                previous_hash="0",
                index=1,
                transactions=[],
            )
            self.chain.append(genesis_block)
            # 새로운 블록체인 저장
            self.save_to_file()

    def create_transaction(self, transaction: Transaction) -> int:
        self.pending_transactions.append(transaction)
        # 트랜잭션 생성 후 저장
        self.save_to_file()
        return self.get_previous_block()["index"] + 1

    def mine_block(self, miner_address: str) -> dict:
        if not self.pending_transactions:
            raise ValueError("No transactions to mine.")

        previous_block = self.get_previous_block()
        previous_proof = previous_block["proof"]
        index = len(self.chain) + 1
        proof = self._proof_of_work(previous_proof, index)
        previous_hash = self._hash(previous_block)

        # 마이너에게 보상 트랜잭션 추가
        system_transaction = Transaction(
            sender="SYSTEM",
            receiver=miner_address,
            nft=None,
            price=0,
        )
        all_transactions = self.pending_transactions.copy()
        all_transactions.append(system_transaction)

        block = self._create_block(
            proof=proof,
            previous_hash=previous_hash,
            index=index,
            transactions=[tx.to_dict() for tx in all_transactions],
        )
        self.chain.append(block)
        self.pending_transactions = []
        # 블록 마이닝 후 저장
        self.save_to_file()
        return block

    def _hash(self, block: dict) -> str:
        encoded_block = _json.dumps(block, sort_keys=True).encode()
        return _hashlib.sha256(encoded_block).hexdigest()

    def _proof_of_work(self, previous_proof: int, index: int) -> int:
        new_proof = 1
        check_proof = False

        while not check_proof:
            to_digest = str(new_proof**2 - previous_proof**2 + index).encode()
            hash_value = _hashlib.sha256(to_digest).hexdigest()

            if hash_value[:4] == "0000":
                check_proof = True
            else:
                new_proof += 1

        return new_proof

    def get_previous_block(self) -> dict:
        return self.chain[-1]

    def _create_block(
        self, proof: int, previous_hash: str, index: int, transactions: List[dict]
    ) -> dict:
        block = {
            "index": index,
            "timestamp": str(_dt.datetime.now()),
            "transactions": transactions,
            "proof": proof,
            "previous_hash": previous_hash,
        }
        return block

    def is_chain_valid(self) -> bool:
        current_block = self.chain[0]
        block_index = 1

        while block_index < len(self.chain):
            next_block = self.chain[block_index]

            # 이전 해시 확인
            if next_block["previous_hash"] != self._hash(current_block):
                print(f"Invalid previous hash at block {block_index}")
                return False

            # 작업 증명 확인
            current_proof = current_block["proof"]
            next_proof = next_block["proof"]
            index = next_block["index"]

            to_digest = str(next_proof**2 - current_proof**2 + index).encode()
            hash_value = _hashlib.sha256(to_digest).hexdigest()
            if hash_value[:4] != "0000":
                print(f"Invalid proof of work at block {block_index}")
                return False

            current_block = next_block
            block_index += 1

        return True

    def get_block_by_index(self, index: int) -> Optional[dict]:
        for block in self.chain:
            if block['index'] == index:
                return block
        return None

    def get_block_by_hash(self, hash_value: str) -> Optional[dict]:
        for block in self.chain:
            block_hash = self._hash(block)
            if block_hash == hash_value:
                return block
        return None

    # 블록체인 저장 메서드 추가
    def save_to_file(self):
        data = {
            'chain': self.chain,
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions]
        }
        with open(self.chain_file, 'w') as f:
            _json.dump(data, f, indent=4)
        print("Blockchain saved to file.")

    # 블록체인 로드 메서드 추가
    def load_from_file(self) -> bool:
        try:
            with open(self.chain_file, 'r') as f:
                data = _json.load(f)
            self.chain = data['chain']
            self.pending_transactions = [Transaction.from_dict(tx) for tx in data['pending_transactions']]
            print("Blockchain loaded from file.")
            return True
        except FileNotFoundError:
            print("Blockchain file not found, starting new blockchain.")
            return False
        except Exception as e:
            print(f"Error loading blockchain from file: {e}")
            return False
