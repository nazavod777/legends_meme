import asyncio.exceptions

import aiohttp.client_exceptions

from utils import logger


async def bypass_errors(target_function,
                        **kwargs) -> any:
    try:
        return await target_function(**kwargs)

    except (asyncio.exceptions.TimeoutError, TimeoutError, aiohttp.client_exceptions.ClientResponseError):
        return await bypass_errors(target_function=target_function,
                                   **kwargs)

    except Exception as error:
        if 'execution reverted: already claimed' in str(error):
            return None

        logger.error(f'Unexpected Error: {error}')

        return await bypass_errors(target_function=target_function,
                             **kwargs)
