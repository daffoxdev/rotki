import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.db.filtering import LedgerActionsFilterQuery
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.types import AssetAmount, Location


def test_serialize_str():
    for entry in LedgerActionType:
        assert isinstance(str(entry), str)

    for entry in LedgerActionType:
        assert isinstance(entry.serialize(), str)


def test_serialize_deserialize_for_db():
    for entry in LedgerActionType:
        db_code = entry.serialize_for_db()
        assert LedgerActionType.deserialize_from_db(db_code) == entry


def test_all_action_types_writtable_in_db(database, function_scope_messages_aggregator):
    db = DBLedgerActions(database, function_scope_messages_aggregator)

    with database.user_write() as cursor:
        query = 'SELECT COUNT(*) FROM ledger_actions WHERE identifier=?'
        for entry in LedgerActionType:
            action = LedgerAction(
                identifier=0,  # whatever
                timestamp=1,
                action_type=entry,
                location=Location.EXTERNAL,
                amount=ONE,
                asset=A_ETH,
                rate=None,
                rate_asset=None,
                link=None,
                notes=None,
            )
            identifier = db.add_ledger_action(cursor, action)
            # Check that changes have been committed to db
            cursor.execute(query, (identifier,))
            assert cursor.fetchone() == (1,)

        assert len(db.get_ledger_actions(
            cursor,
            filter_query=LedgerActionsFilterQuery.make(),
            has_premium=True,
        )) == len(LedgerActionType)


def test_ledger_action_can_be_removed(database, function_scope_messages_aggregator):
    db = DBLedgerActions(database, function_scope_messages_aggregator)
    with database.user_write() as cursor:
        query = 'SELECT COUNT(*) FROM ledger_actions WHERE identifier=?'

        # Add the entry that we want to delete
        action = LedgerAction(
            identifier=0,  # whatever
            timestamp=1,
            action_type=LedgerActionType.INCOME,
            location=Location.EXTERNAL,
            amount=ONE,
            asset=A_ETH,
            rate=None,
            rate_asset=None,
            link=None,
            notes=None,
        )
        identifier = db.add_ledger_action(cursor, action)

        # Delete ledger action
        assert db.remove_ledger_action(cursor, identifier) is None

    with database.conn.read_ctx() as cursor:
        # Check that the change has been committed
        cursor.execute(query, (identifier,))
        assert cursor.fetchone() == (0,)
        assert len(db.get_ledger_actions(
            cursor,
            filter_query=LedgerActionsFilterQuery.make(),
            has_premium=True,
        )) == 0


def test_ledger_action_can_be_edited(database, function_scope_messages_aggregator):
    db = DBLedgerActions(database, function_scope_messages_aggregator)

    query = 'SELECT * FROM ledger_actions WHERE identifier=?'
    # Add the entry that we want to edit
    action = LedgerAction(
        identifier=0,  # whatever
        timestamp=1,
        action_type=LedgerActionType.INCOME,
        location=Location.EXTERNAL,
        amount=ONE,
        asset=A_ETH,
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    )
    with database.user_write() as cursor:
        identifier = db.add_ledger_action(cursor, action)

    # Data for the new entry
    new_entry = LedgerAction(
        identifier=identifier,
        timestamp=2,
        action_type=LedgerActionType.GIFT,
        location=Location.EXTERNAL,
        amount=FVal(3),
        asset=A_ETH,
        rate=FVal(100),
        rate_asset=A_USD,
        link='foo',
        notes='updated',
    )
    assert db.edit_ledger_action(new_entry) is None

    # Check that changes have been committed
    with database.conn.read_ctx() as cursor:
        cursor.execute(query, (identifier,))
        updated_entry = LedgerAction.deserialize_from_db(cursor.fetchone())
        new_entry.identifier = identifier
        assert updated_entry == new_entry

        # now try to see if the optional assets can also be set to None
        new_entry.rate = new_entry.rate_asset = new_entry.link = new_entry.notes = None
        assert db.edit_ledger_action(new_entry) is None
        cursor.execute(query, (identifier,))
        updated_entry = LedgerAction.deserialize_from_db(cursor.fetchone())

    assert updated_entry.rate is None
    assert updated_entry.rate_asset is None
    assert updated_entry.link is None
    assert updated_entry.notes is None


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings, expected', [
    ({'taxable_ledger_actions': [
        LedgerActionType.INCOME,
        LedgerActionType.AIRDROP,
        LedgerActionType.LOSS,
    ]}, FVal('961.425')),  # 578.505 + 478.65 -2*400 + 2*400 - 2 * 47.865
    ({'taxable_ledger_actions': []}, 0),
])
def test_taxable_ledger_action_setting(accountant, expected, google_service):
    """Test that ledger actions respect the taxable setting"""
    history = [
        LedgerAction(
            identifier=1,
            timestamp=1476979735,
            action_type=LedgerActionType.INCOME,
            location=Location.EXTERNAL,
            amount=ONE,  # 578.505 EUR/BTC from mocked prices
            asset=A_BTC,
            rate=None,
            rate_asset=None,
            link=None,
            notes=None,
        ), LedgerAction(
            identifier=2,
            timestamp=1491062063,
            action_type=LedgerActionType.AIRDROP,
            location=Location.EXTERNAL,
            amount=FVal(10),  # 47.865 EUR/ETH from mocked prices
            asset=A_ETH,
            rate=None,
            rate_asset=None,
            link='foo',
            notes='boo',
        ), LedgerAction(
            identifier=3,
            timestamp=1501062063,
            action_type=LedgerActionType.LOSS,
            location=Location.BLOCKCHAIN,
            amount=FVal(2),  # 175.44 EUR/ETH  from mocked prices
            asset=A_ETH,
            rate=FVal(400),  # but should use the given rate of 400 EUR
            rate_asset=A_EUR,
            link='goo',
            notes='hoo',
        ), LedgerAction(  # include a non taxed ledger action too
            identifier=4,
            timestamp=1501062064,
            action_type=LedgerActionType.EXPENSE,
            location=Location.BLOCKCHAIN,
            amount=ONE,
            asset=A_ETH,
            rate=FVal(400),
            rate_asset=A_EUR,
            link='goo2',
            notes='hoo2',
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )
    expected_pnls = PnlTotals()
    if expected != 0:
        expected_pnls[AccountingEventType.LEDGER_ACTION] = PNL(taxable=FVal(expected), free=ZERO)
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_ledger_actions_accounting(accountant, google_service):
    """Test for accounting for ledger actions

    Makes sure that Ledger actions are processed in accounting, range is respected
    and that they contribute to the "bought" amount per asset and that also if
    a rate is given then that is used instead of the queried price
    """
    history = [LedgerAction(  # before range - read only for amount not profit
        identifier=1,
        timestamp=1435979735,  # 0.1 EUR per ETH
        action_type=LedgerActionType.INCOME,
        location=Location.EXTERNAL,
        asset=A_ETH,
        amount=AssetAmount(ONE),
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    ), LedgerAction(
        identifier=2,
        timestamp=1437279735,  # 250 EUR per BTC
        action_type=LedgerActionType.INCOME,
        location=Location.BLOCKCHAIN,
        asset=A_BTC,
        amount=AssetAmount(ONE),
        rate=FVal('400'),
        rate_asset=A_EUR,
        link='foo',
        notes='we give a rate here',
    ), LedgerAction(
        identifier=3,
        timestamp=1447279735,  # 0.4 EUR per XMR
        action_type=LedgerActionType.DIVIDENDS_INCOME,
        location=Location.KRAKEN,
        asset=A_XMR,
        amount=AssetAmount(FVal(10)),
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    ), LedgerAction(
        identifier=4,
        timestamp=1457279735,  # 1 EUR per ETH
        action_type=LedgerActionType.EXPENSE,
        location=Location.EXTERNAL,
        asset=A_ETH,
        amount=AssetAmount(FVal('0.1')),
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    ), LedgerAction(
        identifier=5,
        timestamp=1467279735,  # 420 EUR per BTC
        action_type=LedgerActionType.LOSS,
        location=Location.EXTERNAL,
        asset=A_BTC,
        amount=AssetAmount(FVal('0.1')),
        rate=FVal(500),
        rate_asset=A_USD,
        link='foo2',
        notes='we give a rate here',
    ), LedgerAction(  # after range and should be completely ignored
        identifier=6,
        timestamp=1529693374,
        action_type=LedgerActionType.EXPENSE,
        location=Location.EXTERNAL,
        asset=A_ETH,
        amount=AssetAmount(FVal('0.5')),
        rate=FVal(400),
        rate_asset=A_EUR,
        link='foo3',
        notes='we give a rate here too but doesnt matter',
    )]

    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BTC).is_close('0.9')
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_ETH).is_close('0.9')
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_XMR).is_close('10')
    expected_pnls = PnlTotals({
        # 400 + 0.4*10 - 1*0.1 + 1*0.1 - 1*0.01 - 0.1*500*0.9004 + 0.1*500*0.9004 - 0.1* 400
        AccountingEventType.LEDGER_ACTION: PNL(taxable=FVal('363.99'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)
