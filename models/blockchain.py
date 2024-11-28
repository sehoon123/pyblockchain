# models/blockchain.py
import datetime as _dt
import hashlib as _hashlib
import json as _json
from typing import List, Optional, Set
import requests

class NFT:
    def __init__(
        self,
        name: str,
        description: str,
        image: str,
        dna: str,
        edition: Optional[int] = None,  # Made optional
        date: int = 0,
        attributes: Optional[list] = None,  # Made optional
        compiler: Optional[str] = None,  # Made optional
    ) -> None:
        self.name = name
        self.description = description
        self.image = image
        self.dna = dna
        self.edition = edition
        self.date = date
        self.attributes = attributes if attributes is not None else []
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
            edition=data.get('edition'),  # Handle missing key
            date=data.get('date', 0),  # Provide default if missing
            attributes=data.get('attributes', []),  # Provide default if missing
            compiler=data.get('compiler'),  # Handle missing key
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
        nft_data = data.get('nft')
        nft = NFT.from_dict(nft_data) if nft_data else None
        return Transaction(
            sender=data['sender'],
            receiver=data['receiver'],
            nft=nft,
            price=data['price'],
            timestamp=data.get('timestamp'),
        )

    def __str__(self) -> str:
        return _json.dumps(self.to_dict(), sort_keys=True)


class Blockchain:
    def __init__(self) -> None:
        self.chain: List[dict] = []
        self.pending_transactions: List[Transaction] = []
        self.chain_file = 'blockchain.json'
        self.nodes: Set[str] = set()  # Set to store node addresses

        # Attempt to load the blockchain from file
        if not self.load_from_file():
            # If loading fails, create the genesis block
            genesis_block = self._create_block(
                proof=1,
                previous_hash="0",
                index=1,
                transactions=[],
            )
            self.chain.append(genesis_block)
            # Save the new blockchain to file
            self.save_to_file()

    def _remove_transactions(self, new_block_transactions: List[dict]):
        """
        Remove transactions from pending_transactions that are included in the new block.
        """
        new_block_txs = set()
        for tx in new_block_transactions:
            tx_str = _json.dumps(tx, sort_keys=True)
            new_block_txs.add(tx_str)

        updated_pending = []
        for tx in self.pending_transactions:
            if _json.dumps(tx.to_dict(), sort_keys=True) not in new_block_txs:
                updated_pending.append(tx)
        self.pending_transactions = updated_pending
        self.save_to_file()
        print("Pending transactions updated after adding new block.")

    def add_block(self, block_data: dict) -> bool:
        """
        Add a received block to the chain after verification.
        """
        previous_block = self.get_previous_block()
        if previous_block['index'] + 1 != block_data['index']:
            print(f"Invalid index: expected {previous_block['index'] + 1}, got {block_data['index']}")
            return False

        # Verify previous hash
        previous_block_hash = self._hash(previous_block)
        if previous_block_hash != block_data['previous_hash']:
            print(f"Invalid previous hash: expected {previous_block_hash}, got {block_data['previous_hash']}")
            return False

        if not self.is_chain_valid(self.chain + [block_data]):
            print("Chain validation failed after adding the new block.")
            return False

        self.chain.append(block_data)
        self.save_to_file()
        print(f"Block {block_data['index']} added successfully.")

        # Remove transactions from pending_transactions that are included in the new block
        self._remove_transactions(block_data['transactions'])

        return True

    # Node registration method
    def register_node(self, address: str):
        """
        Register a new node in the network.
        address: Example - 'http://192.168.0.5:5000'
        """
        self.nodes.add(address)
        print(f"Node {address} registered. Total nodes: {len(self.nodes)}")

    # Chain replacement method
    def replace_chain(self) -> bool:
        """
        Replace the chain with the longest one in the network if it's valid.
        """
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)

        for node in network:
            try:
                response = requests.get(f'{node}/api/blockchain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']
                    if length > max_length and self.is_chain_valid(chain):
                        max_length = length
                        longest_chain = chain
            except requests.exceptions.RequestException:
                continue  # Skip nodes that are not reachable

        if longest_chain:
            self.chain = longest_chain
            self.save_to_file()
            print("Chain was replaced with the longest one.")
            return True

        print("Current chain is already the longest.")
        return False

    def create_transaction(self, transaction: Transaction) -> int:
        self.pending_transactions.append(transaction)
        # Save after creating a transaction
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

        # Add a reward transaction for the miner
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
        # Save after mining a block
        self.save_to_file()
        print(f"Block {index} mined successfully.")
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

    def is_chain_valid(self, chain: Optional[List[dict]] = None) -> bool:
        if chain is None:
            chain = self.chain
        current_block = chain[0]
        block_index = 1

        while block_index < len(chain):
            next_block = chain[block_index]

            # Verify previous hash
            if next_block["previous_hash"] != self._hash(current_block):
                print(f"Invalid previous hash at block {block_index}")
                return False

            # Verify proof of work
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

    def save_to_file(self):
        data = {
            'chain': self.chain,
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions]
        }
        with open(self.chain_file, 'w') as f:
            _json.dump(data, f, indent=4)
        print("Blockchain saved to file.")

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
