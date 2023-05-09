import asyncio.exceptions

import web3.auto


async def get_chain_id(provider: web3.auto.Web3) -> int:
    try:
        return await provider.eth.chain_id

    except (asyncio.exceptions.TimeoutError, TimeoutError):
        return await get_chain_id(provider=provider)

    except Exception as error:
        if not str(error):
            return get_chain_id(provider=provider)


async def get_nonce(provider: web3.auto.Web3,
                    address: str) -> int:
    try:
        return await provider.eth.get_transaction_count(address)

    except (asyncio.exceptions.TimeoutError, TimeoutError):
        return await get_nonce(provider=provider,
                               address=address)

    except Exception as error:
        if not str(error):
            return get_nonce(provider=provider,
                             address=address)


async def get_gwei(provider: web3.auto.Web3) -> int:
    try:
        return await provider.eth.gas_price

    except (asyncio.exceptions.TimeoutError, TimeoutError):
        return await get_gwei(provider=provider)

    except Exception as error:
        if not str(error):
            return get_gwei(provider=provider)
