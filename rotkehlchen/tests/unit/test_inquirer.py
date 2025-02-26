import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_AAVE,
    A_BTC,
    A_CRV,
    A_ETH,
    A_EUR,
    A_KFEE,
    A_LINK,
    A_USD,
)
from rotkehlchen.constants.resolver import ChainID, ethaddress_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.inquirer import (
    CURRENT_PRICE_CACHE_SECS,
    CurrentPriceOracle,
    _query_currency_converterapi,
)
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.tests.utils.constants import A_CNY, A_JPY
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import EvmTokenKind, Price, Timestamp
from rotkehlchen.utils.misc import ts_now

UNDERLYING_ASSET_PRICES = {
    A_AAVE: FVal('100'),
    A_LINK: FVal('25'),
    A_CRV: FVal('10'),
    A_USD: FVal('1'),
}


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would contribute in rate limiting of these apis',
)
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_query_realtime_price_apis(inquirer):
    """Query some of the exchange rates APIs we use.

    For x-rates.com we already have a test in externalapis directory
    """
    result = _query_currency_converterapi(A_USD, A_EUR)
    assert result and isinstance(result, FVal)
    result = inquirer.query_historical_fiat_exchange_rates(A_USD, A_CNY, 1411603200)
    assert result == FVal('6.133938')


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would contribute in rate limiting of these apis',
)
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_switching_to_backup_api(inquirer):
    count = 0
    original_get = requests.get

    def mock_xratescom_fail(url, timeout):  # pylint: disable=unused-argument
        nonlocal count
        count += 1
        if 'www.x-rates.com' in url:
            return MockResponse(501, '{"msg": "some error")')
        return original_get(url)

    with patch('requests.get', side_effect=mock_xratescom_fail):
        result = inquirer._query_fiat_pair(A_USD, A_EUR)
        assert result and isinstance(result, FVal)
        assert count > 1, 'requests.get should have been called more than once'


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_fiat_pair_caching(inquirer):
    def mock_xratescom_exchange_rate(from_currency: Asset):  # pylint: disable=unused-argument
        return {A_EUR: FVal('0.9165902841')}

    with patch('rotkehlchen.inquirer.get_current_xratescom_exchange_rates', side_effect=mock_xratescom_exchange_rate):  # noqa: E501
        result = inquirer._query_fiat_pair(A_USD, A_EUR)
        assert result == FVal('0.9165902841')

    # Now outside the mocked response, we should get same value due to caching
    assert inquirer._query_fiat_pair(A_USD, A_EUR) == FVal('0.9165902841')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_fallback_to_cached_values_within_a_month(inquirer):  # pylint: disable=unused-argument
    def mock_api_remote_fail(url, timeout):  # pylint: disable=unused-argument
        return MockResponse(500, '{"msg": "shit hit the fan"')

    # Get a date 15 days ago and insert a cached entry for EUR JPY then
    # Get a date 31 days ago and insert a cache entry for EUR CNY then
    now = ts_now()
    eurjpy_val = Price(FVal('124.123'))
    cache_data = [HistoricalPrice(
        from_asset=A_EUR,
        to_asset=A_JPY,
        source=HistoricalPriceOracle.XRATESCOM,
        timestamp=Timestamp(now - 86400 * 15),
        price=eurjpy_val,
    ), HistoricalPrice(
        from_asset=A_EUR,
        to_asset=A_CNY,
        source=HistoricalPriceOracle.XRATESCOM,
        timestamp=Timestamp(now - 86400 * 31),
        price=Price(FVal('7.719')),
    )]
    GlobalDBHandler().add_historical_prices(cache_data)

    with patch('requests.get', side_effect=mock_api_remote_fail):
        # We fail to find a response but then go back 15 days and find the cached response
        result = inquirer._query_fiat_pair(A_EUR, A_JPY)
        assert result == eurjpy_val
        # The cached response for EUR CNY is too old so we will fail here
        with pytest.raises(RemoteError):
            result = inquirer._query_fiat_pair(A_EUR, A_CNY)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_parsing_forex_cache_works(
        inquirer,
        data_dir,
        mocked_current_prices,
        current_price_oracles_order,
):  # pylint: disable=unused-argument
    price = Price(FVal('124.123'))
    now = ts_now()
    cache_data = [HistoricalPrice(
        from_asset=A_EUR,
        to_asset=A_JPY,
        source=HistoricalPriceOracle.XRATESCOM,
        timestamp=Timestamp(now - 2000),
        price=price,
    )]
    GlobalDBHandler().add_historical_prices(cache_data)
    assert inquirer._query_fiat_pair(A_EUR, A_JPY) == price


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_fallback_to_coingecko(inquirer):  # pylint: disable=unused-argument
    """Cryptocompare does not return current prices for some assets.
    For those we are going to be using coingecko"""
    price = inquirer.find_usd_price(EvmToken('eip155:1/erc20:0xFca59Cd816aB1eaD66534D82bc21E7515cE441CF'))  # RARI # noqa: E501
    assert price != Price(ZERO)
    price = inquirer.find_usd_price(EvmToken('eip155:1/erc20:0x679131F591B4f369acB8cd8c51E68596806c3916'))  # TLN # noqa: E501
    assert price != Price(ZERO)


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_cache(inquirer, freezer):  # pylint: disable=unused-argument
    call_count = 0

    def mock_query_price(from_asset, to_asset):
        assert from_asset.identifier == 'ETH'
        assert to_asset.identifier == 'USD'
        nonlocal call_count
        if call_count == 0:
            price = Price(FVal('1'))
        elif call_count in (1, 2):
            price = Price(FVal('2'))
        else:
            raise AssertionError('Called too many times for this test')

        call_count += 1
        return price

    cc_patch = patch.object(
        inquirer._cryptocompare,
        'query_current_price',
        wraps=mock_query_price,
    )
    inquirer.set_oracles_order(oracles=[CurrentPriceOracle.CRYPTOCOMPARE])

    with cc_patch as cc:
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 1
        assert price == Price(FVal('1'))

        # next time we run, make sure it's the cache
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 1
        assert price == Price(FVal('1'))

        # now move forward in time to invalidate the cache
        freezer.move_to(datetime.fromtimestamp(ts_now() + CURRENT_PRICE_CACHE_SECS + 1))
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 2
        assert price == Price(FVal('2'))

        # also test that ignore_cache works
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 2
        assert price == Price(FVal('2'))
        price = inquirer.find_usd_price(A_ETH, ignore_cache=True)
        assert cc.call_count == 3
        assert price == Price(FVal('2'))


def test_set_oracles_order(inquirer):
    inquirer.set_oracles_order([CurrentPriceOracle.COINGECKO])

    assert inquirer._oracles == [CurrentPriceOracle.COINGECKO]
    assert inquirer._oracle_instances == [inquirer._coingecko]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_all_rate_limited_in_last(inquirer):  # pylint: disable=unused-argument
    """Test zero price is returned when all the oracles have exceeded the rate
    limits requesting the USD price of an asset.
    """
    inquirer._oracle_instances = [
        MagicMock() for oracle in inquirer._oracles if isinstance(oracle, HistoricalPriceOracleInterface)  # noqa: E501
    ]

    for oracle_instance in inquirer._oracle_instances:
        oracle_instance.rate_limited_in_last.return_value = True

    price = inquirer.find_usd_price(A_BTC)

    assert price == Price(ZERO)
    for oracle_instance in inquirer._oracle_instances:
        assert oracle_instance.rate_limited_in_last.call_count == 1
        assert oracle_instance.query_current_price.call_count == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_no_price_found(inquirer):
    """Test zero price is returned when all the oracles returned zero price
    requesting the USD price of an asset.
    """
    inquirer._oracle_instances = [MagicMock() for _ in inquirer._oracles]

    for oracle_instance in inquirer._oracle_instances:
        oracle_instance.query_current_price.return_value = Price(ZERO)

    price = inquirer.find_usd_price(A_BTC)

    assert price == Price(ZERO)
    for oracle_instance in inquirer._oracle_instances:
        assert oracle_instance.query_current_price.call_count == 1


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_via_second_oracle(inquirer):
    """Test price is returned via the second oracle when the first oracle fails
    requesting the USD price of an asset.
    """
    inquirer._oracle_instances = [MagicMock() for _ in inquirer._oracles]

    expected_price = Price(FVal('30000'))
    inquirer._oracle_instances[0].query_current_price.side_effect = RemoteError
    inquirer._oracle_instances[1].query_current_price.return_value = expected_price

    price = inquirer.find_usd_price(A_BTC)

    assert price == expected_price
    for oracle_instance in inquirer._oracle_instances[0:2]:
        assert oracle_instance.query_current_price.call_count == 1


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('mocked_current_prices', [UNDERLYING_ASSET_PRICES])
@pytest.mark.parametrize('ignore_mocked_prices_for', [['YAB', 'USD']])
def test_price_underlying_tokens(inquirer, globaldb):
    aave_weight, link_weight, crv_weight = FVal('0.6'), FVal('0.2'), FVal('0.2')
    address = make_ethereum_address()
    identifier = ethaddress_to_identifier(address)
    token = EvmToken.initialize(
        address=address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Test',
        symbol='YAB',
        underlying_tokens=[
            UnderlyingToken(address=A_AAVE.evm_address, token_kind=EvmTokenKind.ERC20, weight=aave_weight),  # noqa: E501
            UnderlyingToken(address=A_LINK.evm_address, token_kind=EvmTokenKind.ERC20, weight=link_weight),  # noqa: E501
            UnderlyingToken(address=A_CRV.evm_address, token_kind=EvmTokenKind.ERC20, weight=crv_weight),  # noqa: E501
        ],
    )
    globaldb.add_asset(
        asset_id=identifier,
        asset_type=AssetType.EVM_TOKEN,
        data=token,
    )

    price = inquirer.find_price(EvmToken(identifier), A_USD)
    assert price == FVal(67)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_find_uniswap_v2_lp_token_price(inquirer, globaldb, ethereum_manager):
    address = '0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'
    identifier = ethaddress_to_identifier(address)
    inquirer.inject_ethereum(ethereum_manager)
    token = EvmToken.initialize(
        address=address,
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Uniswap LINK/ETH',
        symbol='UNI-V2',
        protocol='UNI-V2',
    )
    globaldb.add_asset(
        asset_id=identifier,
        asset_type=AssetType.EVM_TOKEN,
        data=token,
    )

    price = inquirer.find_uniswap_v2_lp_price(EvmToken(identifier))
    assert price is not None


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_curve_lp_token_price(inquirer_defi, ethereum_manager):
    address = '0xb19059ebb43466C323583928285a49f558E572Fd'
    identifier = ethaddress_to_identifier(address)
    inquirer_defi.inject_ethereum(ethereum_manager)

    price = inquirer_defi.find_curve_pool_price(EvmToken(identifier))
    assert price is not None
    # Check that the protocol is correctly caught by the inquirer
    assert price == inquirer_defi.find_usd_price(EvmToken(identifier))


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_kfee_price(inquirer):
    price = inquirer.find_usd_price(A_KFEE)
    assert FVal(price) == FVal(0.01)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_asset_with_no_api_oracles(inquirer_defi):
    """
    Test that uniswap oracles correctly query USD price of assets
    """
    price = inquirer_defi.find_usd_price(A_1INCH, ignore_cache=True)
    inquirer_defi.set_oracles_order(
        oracles=[CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.CRYPTOCOMPARE],
    )
    price_uni_v2 = inquirer_defi.find_usd_price(A_1INCH, ignore_cache=True)
    inquirer_defi.set_oracles_order(
        oracles=[CurrentPriceOracle.UNISWAPV3, CurrentPriceOracle.CRYPTOCOMPARE],
    )
    price_uni_v3 = inquirer_defi.find_usd_price(A_1INCH, ignore_cache=True)

    assert price != Price(ZERO)
    assert price != price_uni_v2
    assert price.is_close(price_uni_v2, max_diff='0.05')
    assert price.is_close(price_uni_v3, max_diff='0.05')
