import re

from eth_account import Account


def find_keys(input_data: str) -> str | None:
    if not input_data:
        return None

    for value in re.findall(r'\w+', input_data):
        try:
            return Account.from_key(private_key=value).key.hex()

        except ValueError:
            continue

    return None
