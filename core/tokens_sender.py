import asyncio

import web3.main
from web3 import Web3
from web3.auto import w3
from web3.eth import AsyncEth
from web3.types import TxParams

import settings.config
from utils import bypass_errors
from utils import get_address
from utils import get_gwei, get_nonce, get_chain_id
from utils import logger
from utils import read_abi

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,'
              'image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'ru,en;q=0.9,vi;q=0.8,es;q=0.7,cy;q=0.6'
}


class TokensSender:
    def __init__(self,
                 private_key: str,
                 address: str,
                 target_address: str):
        self.token_contract = None
        self.config_json: dict | None = None
        self.provider: web3.main.Web3 | None = None
        self.address: str = address
        self.private_key: str = private_key
        self.target_address: str = target_address

    async def get_token_balance(self) -> int:
        token_balance_units = await bypass_errors(
            target_function=self.token_contract.functions.balanceOf(self.address).call)

        return token_balance_units

    async def send_transaction(self,
                               value: int) -> None:
        tasks = [get_nonce(provider=self.provider,
                           address=self.address),
                 get_chain_id(provider=self.provider)]

        nonce, chain_id = await asyncio.gather(*tasks)

        gwei: float = w3.from_wei(number=await get_gwei(provider=self.provider),
                                  unit='gwei') if self.config_json['GWEI_SENDER'] == 'auto' \
            else float(self.config_json['GWEI_SENDER'])

        if self.config_json['GAS_LIMIT_SENDER'] == 'auto':
            transaction_data: dict = {
                'chainId': chain_id,
                'gasPrice': w3.to_wei(gwei, 'gwei'),
                'from': self.address,
                'nonce': nonce,
                'value': 0
            }

            gas_limit: int = await bypass_errors(self.token_contract.functions.transfer(
                w3.to_checksum_address(value=self.target_address),
                value
            ).estimate_gas,
                                                 transaction=transaction_data)

        else:
            gas_limit: int = int(self.config_json['GAS_LIMIT_SENDER'])

        transaction_data: dict = {
            'chainId': chain_id,
            'gasPrice': w3.to_wei(gwei, 'gwei'),
            'from': self.address,
            'nonce': nonce,
            'value': 0,
            'gas': gas_limit
        }

        transaction: TxParams = await bypass_errors(self.token_contract.functions.transfer(
            w3.to_checksum_address(value=self.target_address),
            value
        ).build_transaction,
                                                    transaction=transaction_data)

        signed_transaction = self.provider.eth.account.sign_transaction(transaction_dict=transaction,
                                                                        private_key=self.private_key)

        await bypass_errors(target_function=self.provider.eth.send_raw_transaction,
                            transaction=signed_transaction.rawTransaction)

        transaction_hash: str = w3.to_hex(w3.keccak(signed_transaction.rawTransaction))
        logger.info(f'{self.address} | {self.private_key} - {transaction_hash}')

    async def start_work(self) -> None:
        self.config_json: dict = settings.config.config
        self.provider: web3.main.Web3 = Web3(Web3.AsyncHTTPProvider(self.config_json['RPC_URL']),
                                             modules={'eth': (AsyncEth,)},
                                             middlewares=[])
        self.token_contract = self.provider.eth.contract(
            address=w3.to_checksum_address(value=self.config_json['TOKEN_CONTRACT_ADDRESS']),
            abi=await read_abi(filename='token_abi.json'))

        token_balance_units: int = await self.get_token_balance()

        await self.send_transaction(value=token_balance_units)


def tokens_sender(input_data: list) -> None:
    private_key, target_address = input_data

    address = get_address(private_key=private_key)

    asyncio.run(TokensSender(private_key=private_key,
                             address=address,
                             target_address=target_address).start_work())
