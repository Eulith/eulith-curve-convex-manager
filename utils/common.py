from typing import Optional

from eulith_web3.erc20 import EulithERC20
from eulith_web3.eulith_web3 import EulithWeb3


def ensure_approval(eulith_web3: EulithWeb3, deposit_token: EulithERC20,
                    deposit_amount: float, pool_address: str) -> Optional[str]:
    pool_allowance = deposit_token.allowance_float(
        eulith_web3.to_checksum_address(eulith_web3.wallet_address),
        eulith_web3.to_checksum_address(pool_address))

    if pool_allowance < deposit_amount:
        approve_tx = deposit_token.approve_float(eulith_web3.to_checksum_address(pool_address),
                                                 deposit_amount, {'from': eulith_web3.wallet_address,
                                                                  'gas': 100000,
                                                                  'maxPriorityFeePerGas': 1000000000})
        app_hash = eulith_web3.eth.send_transaction(approve_tx)
        print(f'Waiting for Curve approval tx to confirm: {app_hash.hex()}')
        eulith_web3.eth.wait_for_transaction_receipt(app_hash)
        return app_hash.hex()
    else:
        return None
