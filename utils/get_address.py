from eth_account import Account


def get_address(private_key: str) -> str | None:
    return Account.from_key(private_key=private_key).address
