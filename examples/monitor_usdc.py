import json
import os
import sys

from eulith_web3.contract_bindings.curve.curve_v2_three_pool import CurveV2ThreePool
from eulith_web3.curve import CurveUtils
from eulith_web3.erc20 import EulithERC20, TokenSymbol
from eulith_web3.eulith_web3 import EulithWeb3, EulithRpcException
from eulith_web3.signing import construct_signing_middleware, LocalSigner
from eulith_web3.uniswap import EulithUniswapPoolLookupRequest, UniswapPoolFee

sys.path.insert(0, os.getcwd())

from utils.banner import print_banner
from utils.settings import EULITH_REFRESH_TOKEN, PRIVATE_KEY
from utils.common import ensure_approval

THREE_POOL_ADDRESS = '0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7'
THREE_POOL_TOKEN = '0x6c3f90f043a72fa612cbac8115ee7e52bde6e490'
CONVEX_BOOSTER_ADDRESS = '0xf403c135812408bfbe8713b5a23a04b3d48aae31'
CONVEX_REWARD_ADDRESS = '0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e'


def deposit_into_curve(eulith_web3: EulithWeb3, deposit_token: EulithERC20, deposit_amount: float) -> str:
    tp = CurveV2ThreePool(ew3, ew3.to_checksum_address(THREE_POOL_ADDRESS))

    ensure_approval(eulith_web3, deposit_token, deposit_amount, THREE_POOL_ADDRESS)

    deposit_amount_int = int(deposit_amount * 10 ** deposit_token.decimals)

    coin0 = tp.coins(0)
    coin1 = tp.coins(1)
    coin2 = tp.coins(2)

    coins = [coin0.lower(), coin1.lower(), coin2.lower()]

    deposit_list = [0, 0, 0]
    deposit_index = coins.index(deposit_token.address.lower())
    deposit_list[deposit_index] = deposit_amount_int

    tx = tp.add_liquidity(deposit_list, 0, {
        'from': eulith_web3.wallet_address,
        'gas': 400000,
        'maxPriorityFeePerGas': 1000000000})
    try:
        tx_hash = ew3.eth.send_transaction(tx)
        ew3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash.hex()
    except EulithRpcException:
        print('\nCurve add liquidity transaction failed: '
              'Looks like you dont have enough gas to complete this transaction. '
              'Please send some more ETH and try again')
        return ''


def unwind(eulith_web3: EulithWeb3) -> str:
    tp = CurveV2ThreePool(ew3, ew3.to_checksum_address(THREE_POOL_ADDRESS))

    lpt = EulithERC20(ew3, ew3.to_checksum_address(THREE_POOL_TOKEN))
    lptb = lpt.balance_of(wallet.address)

    # Assume you want to withdraw USDT to reduce exposure to USDC
    # Magic number 2 to index USDT in the pool's coin list
    remove_liquidity_tx = tp.remove_liquidity_one_coin(lptb, 2, 0, override_tx_parameters={
        'from': wallet.address,
        'gas': 500000,
        'maxPriorityFeePerGas': 1000000000
    })
    unwind_hash = ew3.eth.send_transaction(remove_liquidity_tx)
    eulith_web3.eth.wait_for_transaction_receipt(unwind_hash)
    return unwind_hash.hex()


def new_price_handler(ws, message, eulith_web3):
    dict_message = json.loads(message)
    result = dict_message.get('result', {})

    if type(result) == dict:
        new_price = result.get('data', {}).get('price', None)
        if not new_price:
            print('WARNING: failed to fetch price')
        else:
            print(f'Received new price: 1 USDC = {new_price} USDT')
            # USDC slips by more than 2% off USDT
            if new_price < 0.98:
                unwind_tx_hash = unwind(eulith_web3)
                print(f'Removed liquidity from pool at hash: {unwind_tx_hash}')


def price_error_handler(ws, error, eulith_web3):
    print(error)


if __name__ == '__main__':
    print_banner()

    wallet = LocalSigner(PRIVATE_KEY)
    print(f'\n\nStarting active risk monitoring for wallet {wallet.address}')

    ew3 = EulithWeb3(eulith_url='https://eth-main.eulithrpc.com/v0',
                     eulith_refresh_token=EULITH_REFRESH_TOKEN,
                     signing_middle_ware=construct_signing_middleware(wallet))

    usdc = ew3.v0.get_erc_token(TokenSymbol.USDC)
    usdc_balance = usdc.balance_of_float(wallet.address)

    three_pool = CurveV2ThreePool(ew3, ew3.to_checksum_address(THREE_POOL_ADDRESS))
    curve_utils = CurveUtils(ew3, three_pool)

    lp_token = EulithERC20(ew3, ew3.to_checksum_address(THREE_POOL_TOKEN))

    usdt = ew3.v0.get_erc_token(TokenSymbol.USDT)
    usdc = ew3.v0.get_erc_token(TokenSymbol.USDC)
    wbtc = ew3.v0.get_erc_token(TokenSymbol.WBTC)
    crv = ew3.v0.get_erc_token(TokenSymbol.CRV)
    cvx = ew3.v0.get_erc_token(TokenSymbol.CVX)
    weth = ew3.v0.get_erc_token(TokenSymbol.WETH)

    usdc_usdt_pool = ew3.v0.get_univ3_pool(EulithUniswapPoolLookupRequest(
        token_a=usdc,
        token_b=usdt,
        fee=UniswapPoolFee.FiveBips
    ))

    handle = usdc_usdt_pool.subscribe_prices(new_price_handler, price_error_handler)

    lp_token_balance = lp_token.balance_of(wallet.address)
    print(f'\n{THREE_POOL_ADDRESS} Pool LP token balance: {lp_token_balance}')

    usdt_balance = usdt.balance_of_float(wallet.address)

    ### IF YOU WANT TO DEPOSIT MORE TOKENS ####
    # deposit_into_curve(ew3, usdt, usdt_balance)
