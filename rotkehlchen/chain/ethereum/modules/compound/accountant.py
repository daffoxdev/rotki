from typing import TYPE_CHECKING, Dict

from rotkehlchen.accounting.structures.base import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.ethereum.accounting.structures import TxEventSettings, TxMultitakeTreatment

from .constants import CPT_COMPOUND

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class CompoundAccountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_COMPOUND): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_COMPOUND): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, CPT_COMPOUND): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
            ),
        }
