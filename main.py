import time

from eulith_web3.contract_bindings.curve.curve_v2_tri_crypto import CurveV2TriCrypto
from eulith_web3.contract_bindings.convex.i_convex_deposits import IConvexDeposits
from eulith_web3.contract_bindings.convex.i_reward_staking import IRewardStaking
from eulith_web3.curve import CurveUtils
from eulith_web3.erc20 import EulithERC20, TokenSymbol, EulithWETH
from eulith_web3.eulith_web3 import EulithWeb3
from eulith_web3.signing import construct_signing_middleware, LocalSigner
from eulith_web3.swap import EulithSwapRequest
from eulith_web3.exceptions import EulithRpcException

from utils.settings import PRIVATE_KEY, EULITH_REFRESH_TOKEN
from utils.banner import print_banner

TRI_CRYPTO_POOL_ADDRESS = '0xd51a44d3fae010294c616388b506acda1bfaae46'
CONVEX_BOOSTER_ADDRESS = '0xf403c135812408bfbe8713b5a23a04b3d48aae31'
CONVEX_REWARD_ADDRESS = '0x9D5C5E364D81DaB193b72db9E9BE9D8ee669B652'

if __name__ == '__main__':
    wallet = LocalSigner(PRIVATE_KEY)
    print_banner()

    print(f'RUNNING WITH WALLET ADDRESS: {wallet.address}\n')

    ew3 = EulithWeb3(eulith_url='https://eth-main.eulithrpc.com/v0',
                     eulith_refresh_token=EULITH_REFRESH_TOKEN,
                     signing_middle_ware=construct_signing_middleware(wallet))

    if ew3.eth.get_balance(wallet.address) / 10**18 < 0.06:
        print(f'You need at least 0.06 ETH to run this program. '
              f'Cannot proceed until you fund wallet address: {wallet.address}')
        exit(1)

    usdc = ew3.v0.get_erc_token(TokenSymbol.USDC)

    tri_pool = CurveV2TriCrypto(ew3, ew3.toChecksumAddress(TRI_CRYPTO_POOL_ADDRESS))
    curve_utils = CurveUtils(ew3, tri_pool)
    tokens = curve_utils.get_pool_tokens()

    token_string = 'Curve TriPool Tokens:'
    for i, token in enumerate(tokens):
        token_string += f"  |  Token {i}: {token.symbol}"

    print(token_string)

    lp_token = EulithERC20(ew3, ew3.toChecksumAddress(tri_pool.token()))

    deposit_token = EulithWETH(ew3, tokens[2].address)  # for this particular pool, third token is WETH
    deposit_amount = 0.01
    deposit_amount_wei = deposit_amount * 10 ** deposit_token.decimals

    # [USDT, WBTC, WETH]
    deposit_list = [0, 0, int(deposit_amount_wei)]

    expected_lp_amount = tri_pool.calc_token_amount(deposit_list, False)  # False = use WETH, don't convert from ETH
    expected_lp_amount_float = expected_lp_amount / 10 ** lp_token.decimals

    # Get the price of our deposit token, denominated in USD, so we can calculate our dollar denominated
    # values below
    price, txs = ew3.v0.get_swap_quote(EulithSwapRequest(
        sell_token=usdc,
        buy_token=deposit_token,
        sell_amount=1
    ))

    lp_token_value = curve_utils.get_lp_token_value_denominated_usd()

    dollar_denominated_input = deposit_amount * price
    dollar_denominated_lp_output = expected_lp_amount_float * lp_token_value

    print('\nDepositing some tokens into Curve TriPool')
    print(f'Dollar denominated value IN (deposit): ${round(dollar_denominated_input, 3)}, '
          f'OUT (lp token): ${round(dollar_denominated_lp_output, 3)}\n')

    # ---------- EXECUTE DEPOSIT -------------- #

    deposit_token_balance = deposit_token.balance_of_float(wallet.address)
    if deposit_token_balance < deposit_amount:
        to_deposit = deposit_amount - deposit_token_balance
        deposit_tx = deposit_token.deposit_eth(to_deposit, {'from': wallet.address,
                                                            'gas': 100000,
                                                            'maxPriorityFeePerGas': 1000000000})
        dep_hash = ew3.eth.send_transaction(deposit_tx)
        print(f'Waiting for deposit WETH tx to confirm: {dep_hash.hex()}')
        ew3.eth.wait_for_transaction_receipt(dep_hash)

    pool_allowance = deposit_token.allowance_float(
        ew3.toChecksumAddress(wallet.address),
        ew3.toChecksumAddress(TRI_CRYPTO_POOL_ADDRESS))
    if pool_allowance < deposit_amount:
        approve_tx = deposit_token.approve_float(ew3.toChecksumAddress(TRI_CRYPTO_POOL_ADDRESS),
                                                 deposit_amount, {'from': wallet.address,
                                                                  'gas': 100000,
                                                                  'maxPriorityFeePerGas': 1000000000})
        app_hash = ew3.eth.send_transaction(approve_tx)
        print(f'Waiting for Curve approval tx to confirm: {app_hash.hex()}')
        ew3.eth.wait_for_transaction_receipt(app_hash)

    deposit_to_curve = True  # set false to switch off the below Curve deposit
    if deposit_to_curve:
        min_acceptable_amount = int(expected_lp_amount * 0.99)  # accept 1% slippage on expected
        # Example: https://etherscan.io/tx/0x7e91a8e7a0bb2d9e1c54f282ba1a54e31653cfaa1b24e2478353f298a117e497
        tx = tri_pool.add_liquidity(deposit_list, min_acceptable_amount, {'from': wallet.address,
                                                                          'gas': 400000,
                                                                          'maxPriorityFeePerGas': 1000000000})
        try:
            tx_hash = ew3.eth.send_transaction(tx)
            print(f'Waiting for Curve add liquidity tx to confirm: {tx_hash.hex()}')
            ew3.eth.wait_for_transaction_receipt(tx_hash)
        except EulithRpcException:
            print('\nCurve add liquidity transaction failed: '
                  'Looks like you dont have enough gas to complete this transaction. '
                  'Please send some more ETH to proceed')
            exit(1)

    current_lp_token_balance = lp_token.balance_of(wallet.address)
    while current_lp_token_balance == 0:
        current_lp_token_balance = lp_token.balance_of(wallet.address)
        time.sleep(1)

    print(f'\nCurrent Curve LP token balance: '
          f'{current_lp_token_balance / 10**lp_token.decimals} | LP Token address: {lp_token.address}\n')

    deposit_to_convex = True  # set false to switch off the below Convex deposit
    if current_lp_token_balance > 0 and deposit_to_convex:
        convex_allowance = lp_token.allowance(wallet.address, ew3.toChecksumAddress(CONVEX_BOOSTER_ADDRESS))
        if convex_allowance < current_lp_token_balance:
            to_allow = current_lp_token_balance - convex_allowance
            approve_tx = lp_token.approve(ew3.toChecksumAddress(CONVEX_BOOSTER_ADDRESS),
                                          current_lp_token_balance, {'from': wallet.address,
                                                                     'gas': 100000,
                                                                     'maxPriorityFeePerGas': 1000000000})
            approve_hash = ew3.eth.send_transaction(approve_tx)
            print(f'Waiting for Convex approval tx to confirm: {approve_hash.hex()}')
            ew3.eth.wait_for_transaction_receipt(approve_hash)

        convex_contract = IConvexDeposits(ew3, ew3.toChecksumAddress(CONVEX_BOOSTER_ADDRESS))
        # 38 is the magic number for TriPool that comes from https://www.convexfinance.com/stake
        # True here is to enable stake (to start earning rewards)
        cvx_tx = convex_contract.deposit(38, current_lp_token_balance, True, {'from': wallet.address,
                                                                              'gas': 700000,
                                                                              'maxPriorityFeePerGas': 1000000000})
        try:
            cvx_hash = ew3.eth.send_transaction(cvx_tx)
            print(f'Waiting for Convex deposit tx to confirm: {cvx_hash.hex()}')
            ew3.eth.wait_for_transaction_receipt(cvx_hash)
        except EulithRpcException:
            print('\nDeposit to convex transaction failed. '
                  'Looks like you dont have enough gas to complete this transaction. '
                  'Please send some more ETH to proceed')
            exit(1)

    convex_staking_contract = IRewardStaking(ew3, ew3.toChecksumAddress(CONVEX_REWARD_ADDRESS))

    crv = ew3.v0.get_erc_token(TokenSymbol.CRV)

    while True:
        current_rewards = convex_staking_contract.earned(wallet.address)
        current_rewards_float = current_rewards / 10**crv.decimals

        staked_balance = convex_staking_contract.balance_of(wallet.address)
        print(f'\nConvex staked balance: {staked_balance} | LP Token address: {lp_token.address}')
        print(f'Earned rewards: {current_rewards_float} CRV')

        # The optimal compounding rate depends on your size, which we don't measure in this demo
        # please get in touch with us for a more complete example & calculation
        # This condition just ensures you're not going to spend more on gas than you're claiming
        # which is "minimum viable" for making sense
        if current_rewards_float > 100:
            claim_tx = convex_staking_contract.get_reward({'from': wallet.address,
                                                           'gas': 200000,
                                                           'maxPriorityFeePerGas': 1000000000})
            claim_hash = ew3.eth.send_transaction(claim_tx).hex()
            print(f'Convex claim tx hash: {claim_hash}')

            crv_bal = crv.balance_of_float(wallet.address)
            print(f'New CRV (reward token) balance: {crv_bal}')
        else:
            print('Not enough accumulated reward to justify gas cost of claiming. Skip\n')

        print('Awaiting next block...')
        time.sleep(12)  # blocks on Ethereum come every 11 seconds, circulate around the timing
