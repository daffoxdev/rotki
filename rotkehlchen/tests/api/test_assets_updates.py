import json
import random
import re
from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.resolver import ChainID, strethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.handler import GLOBAL_DB_VERSION
from rotkehlchen.globaldb.updates import ASSETS_VERSION_KEY
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_GLM
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind


def mock_asset_updates(original_requests_get, latest: int, updates: Dict[str, Any], sql_actions: Dict[str, str]):  # noqa: E501

    def mock_requests_get(url, *args, **kwargs):  # pylint: disable=unused-argument
        if 'github' not in url:
            return original_requests_get(url, *args, **kwargs)

        if 'updates/info.json' in url:
            response = f'{{"latest": {latest}, "updates": {json.dumps(updates)}}}'
        elif 'updates.sql' in url:
            match = re.search(r'.*/(\d+)/updates.sql', url)
            assert match, f'Couldnt extract version from {url}'
            version = match.group(1)
            action = sql_actions.get(version)
            assert action is not None, f'Could not find SQL action for version {version}'
            response = action
        else:
            raise AssertionError(f'Unrecognized argument url for assets update mock in tests: {url}')  # noqa: E501

        return MockResponse(200, response)

    return patch('requests.get', side_effect=mock_requests_get)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_simple_update(rotkehlchen_api_server, globaldb):
    """Test that the happy case of update works.

    - Test that up_to_version argument works
    - Test that only versions above current local are applied
    - Test that versions with min/max schema mismatch are skipped
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_4 = """INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c", "A", "A", "0xC2FEC534c461c45533e142f724d0e3930650929c", 18, NULL);INSERT INTO assets(identifier,type, started, swapped_for) VALUES("eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c", "C", 123, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c", "AKB token", "AKB", NULL, "AIDU", NULL);
*
INSERT INTO assets(identifier,type, started, swapped_for) VALUES("121-ada-FADS-as", "F", NULL, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("121-ada-FADS-as", "A name", "SYMBOL", "", "", "BTC");
*
UPDATE common_asset_details SET name="Ευρώ" WHERE identifier="EUR";
INSERT INTO assets(identifier,type, started, swapped_for) VALUES("EUR", "A", NULL, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("EUR", "Ευρώ", "EUR", NULL, NULL, NULL);
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999996,
        updates={
            "999999991": {
                "changes": 1,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999992": {
                "changes": 1,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999993": {
                "changes": 5,
                "min_schema_version": GLOBAL_DB_VERSION - 2,
                "max_schema_version": GLOBAL_DB_VERSION - 1,
            },
            "999999994": {
                "changes": 3,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999995": {
                "changes": 2,
                "min_schema_version": GLOBAL_DB_VERSION,
                "max_schema_version": GLOBAL_DB_VERSION,
            },
            "999999996": {
                "changes": 5,
                "min_schema_version": GLOBAL_DB_VERSION + 1,
                "max_schema_version": GLOBAL_DB_VERSION + 2,
            },
            "999999997": {
                "changes": 5,
                "min_schema_version": GLOBAL_DB_VERSION + 1,
                "max_schema_version": GLOBAL_DB_VERSION + 2,
            },
        },
        sql_actions={"999999991": "", "999999992": "", "999999993": "", "999999994": update_4, "999999995": "", "999999996": ""},  # noqa: E501
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999992)
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            result = outcome['result']
            assert outcome['message'] == ''
        else:
            result = assert_proper_response_with_result(response)
        assert result['local'] == 999999992
        assert result['remote'] == 999999996
        assert result['new_changes'] == 5  # 994 (3) + 995(2)

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query, 'up_to_version': 999999997},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 2
        assert 'Skipping assets update 999999993 since it requires a min schema of 1 and max schema of 2 while the local DB schema version is 3. You will have to follow an alternative method to obtain the assets of this update. Easiest would be to reset global DB' in warnings[0]  # noqa: E501
        assert 'Skipping assets update 999999996 since it requires a min schema of 4. Please upgrade rotki to get this assets update' in warnings[1]  # noqa: E501

        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999995
        new_token = EvmToken('eip155:1/erc20:0xC2FEC534c461c45533e142f724d0e3930650929c')
        assert new_token.identifier == strethaddress_to_identifier('0xC2FEC534c461c45533e142f724d0e3930650929c')  # noqa: E501
        assert new_token.name == 'AKB token'
        assert new_token.symbol == 'AKB'
        assert new_token.asset_type == AssetType.EVM_TOKEN
        assert new_token.started == 123
        assert new_token.forked is None
        assert new_token.swapped_for is None
        assert new_token.coingecko is None
        assert new_token.cryptocompare == 'AIDU'
        assert new_token.evm_address == '0xC2FEC534c461c45533e142f724d0e3930650929c'
        assert new_token.decimals == 18
        assert new_token.protocol is None

        new_asset = Asset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''

        assert Asset('EUR').name == 'Ευρώ'


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_update_conflicts(rotkehlchen_api_server, globaldb):
    """Test that conflicts in an asset update are handled properly"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier,type, started, swapped_for) VALUES("121-ada-FADS-as", "F", NULL, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("121-ada-FADS-as", "A name", "SYMBOL", "", "", "BTC");
*
INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F", "A", "A", "0x6B175474E89094C44Da98b954EedeAC495271d0F", 8, "maker");INSERT INTO assets(identifier,type, started, swapped_for) VALUES("eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F", "C", 1573672677, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F", "New Multi Collateral DAI", "NDAI", "dai", NULL, NULL)
*
INSERT INTO assets(identifier,type, started, swapped_for) VALUES("DASH", "B", 1337, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("DASH", "Dash", "DASH", "dash-coingecko", NULL, "BTC");
*
INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F", "A", "A", "0x1B175474E89094C44Da98b954EedeAC495271d0F", 18, NULL);INSERT INTO assets(identifier,type, started, swapped_for) VALUES("eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F", "C", 1573672677, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F", "Conflicting token", "CTK", "ctk", NULL, NULL)
*
    """  # noqa: E501
    globaldb.add_asset(  # add a conflicting token
        asset_id='eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F',
        asset_type=AssetType.EVM_TOKEN,
        data=EvmToken.initialize(
            address=ChecksumEvmAddress('0x1B175474E89094C44Da98b954EedeAC495271d0F'),
            chain=ChainID.ETHEREUM,
            token_kind=EvmTokenKind.ERC20,
            decimals=12,
            name='Conflicting token',
            symbol='CTK',
            started=None,
            swapped_for=None,
            coingecko='ctk',
            cryptocompare=None,
            protocol=None,
            underlying_tokens=None,
        ),
    )
    globaldb.add_user_owned_assets([Asset('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F')])  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999991,
        updates={"999999991": {
            "changes": 3,
            "min_schema_version": GLOBAL_DB_VERSION,
            "max_schema_version": GLOBAL_DB_VERSION,
        }},
        sql_actions={"999999991": update_1},
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999990)
    start_assets_num = len(globaldb.get_all_asset_data(mapping=False))
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            result = outcome['result']
            assert outcome['message'] == ''
        else:
            result = assert_proper_response_with_result(response)
        assert result['local'] == 999999990
        assert result['remote'] == 999999991
        assert result['new_changes'] == 3

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == 'Found conflicts during assets upgrade'
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(
                response,
                message='Found conflicts during assets upgrade',
                status_code=HTTPStatus.CONFLICT,
            )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999990
        assert len(globaldb.get_all_asset_data(mapping=False)) == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as')
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get 3 conflicts
        expected_result = [{
            'identifier': 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'local': {
                'name': 'Multi Collateral Dai',
                'symbol': 'DAI',
                'asset_type': 'evm token',
                'started': 1573672677,
                'forked': None,
                'swapped_for': None,
                'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'dai',
                'protocol': None,
            },
            'remote': {
                'name': 'New Multi Collateral DAI',
                'symbol': 'NDAI',
                'asset_type': 'evm token',
                'started': 1573672677,
                'forked': None,
                'swapped_for': None,
                'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 8,
                'cryptocompare': None,
                'coingecko': 'dai',
                'protocol': 'maker',
            },
        }, {
            'identifier': 'DASH',
            'local': {
                'name': 'Dash',
                'symbol': 'DASH',
                'asset_type': 'own chain',
                'started': 1390095618,
                'forked': None,
                'swapped_for': None,
                'address': None,
                'chain': None,
                'token_kind': None,
                'decimals': None,
                'cryptocompare': None,
                'coingecko': 'dash',
                'protocol': None,
            },
            'remote': {
                'name': 'Dash',
                'symbol': 'DASH',
                'asset_type': 'own chain',
                'started': 1337,
                'forked': 'BTC',
                'swapped_for': None,
                'address': None,
                'chain': None,
                'token_kind': None,
                'decimals': None,
                'cryptocompare': None,
                'coingecko': 'dash-coingecko',
                'protocol': None,
            },
        }, {
            'identifier': 'eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F',
            'local': {
                'asset_type': 'evm token',
                'coingecko': 'ctk',
                'cryptocompare': None,
                'decimals': 12,
                'address': '0x1B175474E89094C44Da98b954EedeAC495271d0F',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'forked': None,
                'name': 'Conflicting token',
                'protocol': None,
                'started': None,
                'swapped_for': None,
                'symbol': 'CTK',
            },
            'remote': {
                'asset_type': 'evm token',
                'coingecko': 'ctk',
                'cryptocompare': None,
                'decimals': 18,
                'address': '0x1b175474E89094C44DA98B954EeDEAC495271d0f',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'forked': None,
                'name': 'Conflicting token',
                'protocol': None,
                'started': 1573672677,
                'swapped_for': None,
                'symbol': 'CTK',
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F': 'remote', 'DASH': 'local', 'eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F': 'remote'}  # noqa: E501
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query, 'conflicts': conflicts},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(
                response,
                message='',
                status_code=HTTPStatus.OK,
            )

        cursor = globaldb.conn.cursor()
        # check conflicts were solved as per the given choices and new asset also added
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999991
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        dai = EvmToken('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F')
        assert dai.identifier == strethaddress_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F')  # noqa: E501
        assert dai.name == 'New Multi Collateral DAI'
        assert dai.symbol == 'NDAI'
        assert dai.asset_type == AssetType.EVM_TOKEN
        assert dai.started == 1573672677
        assert dai.forked is None
        assert dai.swapped_for is None
        assert dai.coingecko == 'dai'
        assert dai.cryptocompare is None
        assert dai.evm_address == '0x6B175474E89094C44Da98b954EedeAC495271d0F'
        assert dai.decimals == 8
        assert dai.protocol == 'maker'
        # make sure data is in both tables
        assert cursor.execute('SELECT COUNT(*) from evm_tokens WHERE address="0x6B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501

        dash = Asset('DASH')
        assert dash.identifier == 'DASH'
        assert dash.name == 'Dash'
        assert dash.symbol == 'DASH'
        assert dash.asset_type == AssetType.OWN_CHAIN
        assert dash.started == 1390095618
        assert dash.forked is None
        assert dash.swapped_for is None
        assert dash.coingecko == 'dash'
        assert dash.cryptocompare is None
        assert cursor.execute('SELECT COUNT(*) from common_asset_details WHERE identifier="DASH";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="DASH";').fetchone()[0] == 1  # noqa: E501

        new_asset = Asset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''
        assert cursor.execute('SELECT COUNT(*) from common_asset_details WHERE identifier="121-ada-FADS-as";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="121-ada-FADS-as";').fetchone()[0] == 1  # noqa: E501

        ctk = EvmToken('eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F')
        assert ctk.name == 'Conflicting token'
        assert ctk.symbol == 'CTK'
        assert ctk.asset_type == AssetType.EVM_TOKEN
        assert ctk.started == 1573672677
        assert ctk.forked is None
        assert ctk.swapped_for is None
        assert ctk.coingecko == 'ctk'
        assert ctk.cryptocompare is None
        assert ctk.evm_address == '0x1B175474E89094C44Da98b954EedeAC495271d0F'
        assert ctk.decimals == 18
        assert ctk.protocol is None
        assert cursor.execute('SELECT COUNT(*) from evm_tokens WHERE address="0x1B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) from assets WHERE identifier="eip155:1/erc20:0x1B175474E89094C44Da98b954EedeAC495271d0F";').fetchone()[0] == 1  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_foreignkey_conflict(rotkehlchen_api_server, globaldb):
    """Test that when a conflict that's not solvable happens the entry is ignored

    One such case is when the update of an asset would violate a foreign key constraint.
    So we try to update the swapped_for to a non existing asset and make sure it's skipped.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier,type, started, swapped_for) VALUES("121-ada-FADS-as", "F", NULL, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("121-ada-FADS-as", "A name", "SYMBOL", "", "", "BTC");
*
UPDATE assets SET swapped_for="eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972" WHERE identifier="eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d";
INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "A", "A", "0xa74476443119A942dE498590Fe1f2454d7D4aC0d", 18, NULL);INSERT INTO assets(identifier,type, started, swapped_for) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "C", 1478810650, "eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972"); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "Golem", "GNT", "golem", NULL, NULL)
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=999999991,
        updates={"999999991": {
            "changes": 2,
            "min_schema_version": GLOBAL_DB_VERSION,
            "max_schema_version": GLOBAL_DB_VERSION,
        }},
        sql_actions={"999999991": update_1},
    )
    globaldb.add_setting_value(ASSETS_VERSION_KEY, 999999990)
    start_assets_num = len(globaldb.get_all_asset_data(mapping=False))
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            result = outcome['result']
            assert outcome['message'] == ''
        else:
            result = assert_proper_response_with_result(response)
        assert result['local'] == 999999990
        assert result['remote'] == 999999991
        assert result['new_changes'] == 2

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == 'Found conflicts during assets upgrade'
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(
                response,
                message='Found conflicts during assets upgrade',
                status_code=HTTPStatus.CONFLICT,
            )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999990
        assert len(globaldb.get_all_asset_data(mapping=False)) == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as')
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get a conflict
        expected_result = [{
            'identifier': 'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
            'local': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
            'remote': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d': 'remote'}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'async_query': async_query, 'conflicts': conflicts},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
            )
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(
                response,
                message='',
                status_code=HTTPStatus.OK,
            )

        # check new asset was added and conflict was ignored with an error due to
        # inability to do anything with the missing swapped_for
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, None) == 999999991
        gnt = EvmToken('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d')
        assert gnt.identifier == strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')  # noqa: E501
        assert gnt.name == 'Golem'
        assert gnt.symbol == 'GNT'
        assert gnt.asset_type == AssetType.EVM_TOKEN
        assert gnt.started == 1478810650
        assert gnt.forked is None
        assert gnt.swapped_for == A_GLM.identifier
        assert gnt.coingecko == 'golem'
        assert gnt.cryptocompare is None
        assert gnt.evm_address == '0xa74476443119A942dE498590Fe1f2454d7D4aC0d'
        assert gnt.decimals == 18
        assert gnt.protocol is None

        new_asset = Asset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''

        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 1
        assert f'Failed to resolve conflict for {gnt.identifier} in the DB during the v999999991 assets update. Skipping entry' in warnings[0]  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_update_from_early_clean_db(rotkehlchen_api_server, globaldb):
    """
    Test that if the asset upgrade happens from a very early DB that has had no assets
    version key set we still upgrade properly and set the assets version properly.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    update_1 = """INSERT INTO assets(identifier,type, started, swapped_for) VALUES("121-ada-FADS-as", "F", NULL, NULL); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("121-ada-FADS-as", "A name", "SYMBOL", "", "", "BTC");
*
UPDATE assets SET swapped_for="eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972" WHERE identifier="eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d";
INSERT INTO evm_tokens(identifier, token_kind, chain, address, decimals, protocol) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "A", "A", "0xa74476443119A942dE498590Fe1f2454d7D4aC0d", 18, NULL);INSERT INTO assets(identifier,type, started, swapped_for) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "C", 1478810650, "eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972"); INSERT INTO common_asset_details(identifier, name, symbol, coingecko, cryptocompare, forked) VALUES("eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d", "Golem", "GNT", "golem", NULL, NULL)
    """  # noqa: E501
    update_patch = mock_asset_updates(
        original_requests_get=requests.get,
        latest=1,
        updates={"1": {
            "changes": 2,
            "min_schema_version": GLOBAL_DB_VERSION,
            "max_schema_version": GLOBAL_DB_VERSION,
        }},
        sql_actions={"1": update_1},
    )
    cursor = globaldb.conn.cursor()
    cursor.execute(f'DELETE FROM settings WHERE name="{ASSETS_VERSION_KEY}"')
    start_assets_num = len(globaldb.get_all_asset_data(mapping=False))
    with update_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
        )
        result = assert_proper_response_with_result(response)
        assert result['local'] == 0
        assert result['remote'] == 1
        assert result['new_changes'] == 2

        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
        )
        result = assert_proper_response_with_result(
            response,
            message='Found conflicts during assets upgrade',
            status_code=HTTPStatus.CONFLICT,
        )

        # Make sure that nothing was committed
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 0
        assert len(globaldb.get_all_asset_data(mapping=False)) == start_assets_num
        with pytest.raises(UnknownAsset):
            Asset('121-ada-FADS-as')
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 0, f'Found warnings: {warnings}'
        # See that we get a conflict
        expected_result = [{
            'identifier': 'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
            'local': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0x7DD9c5Cba05E151C895FDe1CF355C9A1D5DA6429',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
            'remote': {
                'name': 'Golem',
                'symbol': 'GNT',
                'asset_type': 'evm token',
                'started': 1478810650,
                'forked': None,
                'swapped_for': 'eip155:1/erc20:0xA8d35739EE92E69241A2Afd9F513d41021A07972',
                'address': '0xa74476443119A942dE498590Fe1f2454d7D4aC0d',
                'chain': 'ethereum',
                'token_kind': 'erc20',
                'decimals': 18,
                'cryptocompare': None,
                'coingecko': 'golem',
                'protocol': None,
            },
        }]
        assert result == expected_result

        # now try the update again but specify the conflicts resolution
        conflicts = {'eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d': 'remote'}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'assetupdatesresource',
            ),
            json={'conflicts': conflicts},
        )
        result = assert_proper_response_with_result(
            response,
            message='',
            status_code=HTTPStatus.OK,
        )

        # check new asset was added and conflict was ignored with an error due to
        # inability to do anything with the missing swapped_for
        assert result is True
        assert globaldb.get_setting_value(ASSETS_VERSION_KEY, 0) == 1
        gnt = EvmToken('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d')
        assert gnt.identifier == strethaddress_to_identifier('0xa74476443119A942dE498590Fe1f2454d7D4aC0d')  # noqa: E501
        assert gnt.name == 'Golem'
        assert gnt.symbol == 'GNT'
        assert gnt.asset_type == AssetType.EVM_TOKEN
        assert gnt.started == 1478810650
        assert gnt.forked is None
        assert gnt.swapped_for == A_GLM.identifier
        assert gnt.coingecko == 'golem'
        assert gnt.cryptocompare is None
        assert gnt.evm_address == '0xa74476443119A942dE498590Fe1f2454d7D4aC0d'
        assert gnt.decimals == 18
        assert gnt.protocol is None

        new_asset = Asset('121-ada-FADS-as')
        assert new_asset.identifier == '121-ada-FADS-as'
        assert new_asset.name == 'A name'
        assert new_asset.symbol == 'SYMBOL'
        assert new_asset.asset_type == AssetType.COUNTERPARTY_TOKEN
        assert new_asset.started is None
        assert new_asset.forked == 'BTC'
        assert new_asset.swapped_for is None
        assert new_asset.coingecko == ''
        assert new_asset.cryptocompare == ''

        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0, f'Found errors: {errors}'
        assert len(warnings) == 1
        assert f'Failed to resolve conflict for {gnt.identifier} in the DB during the v1 assets update. Skipping entry' in warnings[0]  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_update_no_user_loggedin(rotkehlchen_api_server):
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetupdatesresource',
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='No user is currently logged in',
        status_code=HTTPStatus.CONFLICT,
    )
