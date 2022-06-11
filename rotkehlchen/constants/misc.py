from rotkehlchen.assets.types import AssetType
from rotkehlchen.fval import FVal
from rotkehlchen.types import EventType

EV_BUY = EventType('buy')
EV_SELL = EventType('sell')
EV_ASSET_MOVE = EventType('asset_movement')
EV_LOAN_SETTLE = EventType('loan_settlement')
EV_INTEREST_PAYMENT = EventType('interest_rate_payment')
EV_MARGIN_CLOSE = EventType('margin_position_close')
EV_DEFI = EventType('defi_event')
EV_LEDGER_ACTION = EventType('ledger_action')
EV_STAKING_REWARD = EventType('staking_reward')

CURRENCYCONVERTER_API_KEY = '7ad371210f296db27c19'

ZERO = FVal(0)
ONE = FVal(1)
EXP18 = FVal(1e18)

NFT_DIRECTIVE = '_nft_'

# API URLS
KRAKEN_BASE_URL = 'https://api.kraken.com'
KRAKEN_API_VERSION = '0'
# KRAKEN_BASE_URL = 'http://localhost:5001/kraken'
# KRAKEN_API_VERSION = 'mock'
# BINANCE_BASE_URL = 'http://localhost:5001/binance/api/'

ASSET_TYPES_EXCLUDED_FOR_USERS = {AssetType.NFT}
