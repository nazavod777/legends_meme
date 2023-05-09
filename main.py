from multiprocessing.dummy import Pool

from web3.auto import w3

from core import tokens_claimer
from core import tokens_sender
from utils import find_keys
from utils import logger

if __name__ == '__main__':
    accounts_list: list = []

    with open('accounts.txt', 'r', encoding='utf-8-sig') as file:
        for row in file:
            target_private_key = find_keys(input_data=row.strip())

            if target_private_key:
                accounts_list.append(target_private_key)

    logger.info(f'Загружено {len(accounts_list)} аккаунтов')

    user_action: int = int(input('\n1. Tokens Claimer\n'
                                 '2. Tokens Transfer\n'
                                 'Select Your Action: '))

    threads: int = int(input('Threads: '))

    match user_action:
        case 1:
            with Pool(processes=threads) as executor:
                executor.map(tokens_claimer, accounts_list)

        case 2:
            target_address: str = w3.to_checksum_address(value=input('Enter Address To Sending Tokens: '))

            with Pool(processes=threads) as executor:
                executor.map(tokens_sender, [[current_account, target_address] for current_account in accounts_list])

        case _:
            pass

    logger.success('Работа успешно завершена')
    input('\nPress Enter To Exit..')
