from abc import ABCMeta, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional

from rotkehlchen.accounting.pnl import (
    OVR_ASSET_MOVEMENTS_FEES,
    OVR_LEDGER_ACTIONS_PNL,
    OVR_LOAN_PROFIT,
    OVR_MARGIN_PNL,
    OVR_STAKING,
    OVR_TRADE_PNL,
)
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.accounting.structures import ActionType


class AccountingEventType(Enum):
    TRADE = auto()
    ASSET_MOVEMENT = auto()
    MARGIN_POSITION = auto()
    LOAN = auto()
    PREFORK_ACQUISITION = auto()
    LEDGER_ACTION = auto()
    STAKING = auto()
    HISTORY_BASE_ENTRY = auto()
    TRANSACTION_EVENT = auto()

    def to_pnl_overview_str(self) -> str:
        """Turns to pnl overview string for known types

        For others returns other (should not happen and should be filled in by processor function)
        """
        return TYPE_TO_STR.get(self, 'other')


TYPE_TO_STR = {
    AccountingEventType.TRADE: OVR_TRADE_PNL,
    AccountingEventType.ASSET_MOVEMENT: OVR_ASSET_MOVEMENTS_FEES,
    AccountingEventType.MARGIN_POSITION: OVR_MARGIN_PNL,
    AccountingEventType.LOAN: OVR_LOAN_PROFIT,
    AccountingEventType.LEDGER_ACTION: OVR_LEDGER_ACTIONS_PNL,
    AccountingEventType.STAKING: OVR_STAKING,
}


class AccountingEventMixin(metaclass=ABCMeta):
    """Interface to be followed by all data structures that go in accounting"""

    @abstractmethod
    def get_timestamp(self) -> Timestamp:
        """Get the event's timestamp"""
        ...

    @staticmethod
    @abstractmethod
    def get_accounting_event_type() -> AccountingEventType:
        """
        Returns the event type for accounting
        """
        ...

    @abstractmethod
    def get_identifier(self) -> str:
        """Get a unique identifier from an accounting event"""
        ...

    @abstractmethod
    def should_ignore(self, ignored_ids_mapping: Dict['ActionType', List[str]]) -> bool:
        """Returns whether this event should be ignored due to user settings"""
        ...

    @abstractmethod
    def get_assets(self) -> None:
        """Gets the assets involved in the event.

        May raise:
        - UnknownAsset, UnsupportedAsset due to the trade pair's assets
        - UnprocessableTradePair: If a trade's pair can't be processed
        """
        ...

    @abstractmethod
    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],
    ) -> int:
        """Processes the event for accounting and adds to the respective pot's processed events.

        Can also accept the iterator of the processed events of the accounting pot if there is
        a need to pull multiple events from the iterator (e.g. for defi swaps)

        Returns the number of events consumed.
        """
        ...
