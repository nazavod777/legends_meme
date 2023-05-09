import asyncio

import aiohttp
import web3.main
from eth_account.messages import encode_defunct
from pyuseragents import random as random_useragent
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
    'accept-language': 'ru,en;q=0.9,vi;q=0.8,es;q=0.7,cy;q=0.6',
    'content-type': 'application/json;charset=UTF-8'
}


class TokensClaimer:
    def __init__(self,
                 private_key: str,
                 address: str):
        self.claim_contract = None
        self.config_json: dict | None = None
        self.provider: web3.main.Web3 | None = None
        self.address: str = address
        self.private_key: str = private_key

    async def get_sign_data(self) -> dict:
        while True:
            try:
                async with aiohttp.ClientSession(headers={
                    **headers,
                    'user-agent': random_useragent()
                }) as session:
                    r = await bypass_errors(target_function=session.get,
                                            url=f'https://api.unitag.xyz:11211/api/frontend/Authentication/signMsg/LEGENDS/{self.address}')

                    if not (await r.json()).get('content'):
                        logger.error(f'{self.address} | {self.private_key} - Wrong Response: {await r.text()}')
                        continue

                    return await r.json()

            except Exception as error:
                logger.error(f'{self.address} | {self.private_key} - Unexpected Error: {error}')

    async def send_transaction(self,
                               signature: str,
                               ref_address: str) -> None:
        tasks = [get_nonce(provider=self.provider,
                           address=self.address),
                 get_chain_id(provider=self.provider)]

        nonce, chain_id = await asyncio.gather(*tasks)

        gwei: float = w3.from_wei(number=await get_gwei(provider=self.provider),
                                  unit='gwei') if self.config_json['GWEI_CLAIM'] == 'auto' \
            else float(self.config_json['GWEI_CLAIM'])

        if self.config_json['GAS_LIMIT_CLAIM'] == 'auto':
            transaction_data: dict = {
                'chainId': chain_id,
                'gasPrice': w3.to_wei(gwei, 'gwei'),
                'from': self.address,
                'nonce': nonce,
                'value': 0
            }

            gas_limit: int = await bypass_errors(self.claim_contract.functions.claim(
                ref_address,
                signature
            ).estimate_gas,
                                                 transaction=transaction_data)

            if gas_limit is None:
                return

        else:
            gas_limit: int = int(self.config_json['GAS_LIMIT_CLAIM'])

        transaction_data: dict = {
            'chainId': chain_id,
            'gasPrice': w3.to_wei(gwei, 'gwei'),
            'from': self.address,
            'nonce': nonce,
            'value': 0,
            'gas': gas_limit
        }

        transaction: TxParams = await bypass_errors(self.claim_contract.functions.claim(
            ref_address,
            signature
        ).build_transaction,
                                                    transaction=transaction_data)

        signed_transaction = self.provider.eth.account.sign_transaction(transaction_dict=transaction,
                                                                        private_key=self.private_key)

        await bypass_errors(target_function=self.provider.eth.send_raw_transaction,
                            transaction=signed_transaction.rawTransaction)

        transaction_hash: str = w3.to_hex(w3.keccak(signed_transaction.rawTransaction))
        logger.info(f'{self.address} | {self.private_key} - {transaction_hash}')

    async def send_signature(self,
                             signature: str) -> str | None:
        async with aiohttp.ClientSession(headers={
            **headers,
            'user-agent': random_useragent()
        }) as session:
            async with session.put(
                    f'https://api.unitag.xyz:11211/api/frontend/Authentication/login/LEGENDS/{self.address}',
                    json={
                        'parent': '8311f6bc',
                        'signature': signature
                    }) as r:
                if (await r.json()).get('content') and (await r.json())['content'].get('token'):
                    return (await r.json())['content']['token']

        return None

    @staticmethod
    async def get_transaction_data(bearer_token: str) -> tuple[str, str] | None:
        async with aiohttp.ClientSession(headers={
            **headers,
            'user-agent': random_useragent(),
            'authorization': f'Bearer {bearer_token}'
        }) as session:
            async with session.get('https://api.legends.vip:16001/api/frontend/Airdrop') as r:
                if (await r.json()).get('content') and (await r.json())['content'].get('refAccount') and \
                        (await r.json())['content'].get('signature'):
                    return (await r.json())['content']['refAccount'], (await r.json())['content']['signature']

        return None

    async def start_work(self) -> None:
        self.config_json: dict = settings.config.config
        self.provider: web3.main.Web3 = Web3(Web3.AsyncHTTPProvider(self.config_json['RPC_URL']),
                                             modules={'eth': (AsyncEth,)},
                                             middlewares=[])
        self.claim_contract = self.provider.eth.contract(
            address=w3.to_checksum_address(value=self.config_json['CLAIM_CONTRACT_ADDRESS']),
            abi=await read_abi(filename='claim_abi.json'))
        message_response_json: dict = await self.get_sign_data()
        message_text: str | None = message_response_json['content']

        if not message_text:
            return

        signature = w3.eth.account.sign_message(encode_defunct(text=message_text),
                                                private_key=self.private_key).signature.hex()
        bearer_token: str | None = await self.send_signature(signature=signature)

        if not bearer_token:
            return

        transaction_data: tuple[str | str] | None = await self.get_transaction_data(bearer_token=bearer_token)

        if not transaction_data:
            return

        await self.send_transaction(signature=transaction_data[1],
                                    ref_address=transaction_data[0])


def tokens_claimer(private_key: str) -> None:
    address = get_address(private_key=private_key)

    asyncio.run(TokensClaimer(private_key=private_key,
                              address=address).start_work())
