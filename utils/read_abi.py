import json

import aiofiles


async def read_abi(filename: str) -> str:
    async with aiofiles.open(f'./abies/{filename}') as file:
        json_data = await file.read()

        return json.dumps(json.loads(json_data))
