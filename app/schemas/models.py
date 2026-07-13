from pydantic import BaseModel


class TokenPrice(BaseModel):
    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    market_cap_rank: int | None = None
    total_volume: float
    price_change_percentage_24h: float
    price_change_percentage_7d: float | None = None
    circulating_supply: float
    total_supply: float | None = None
    ath: float
    ath_change_percentage: float


class TokenDetail(BaseModel):
    id: str
    symbol: str
    name: str
    description: str
    current_price: float
    market_cap: float
    market_cap_rank: int | None = None
    total_volume: float
    high_24h: float
    low_24h: float
    price_change_percentage_24h: float
    price_change_percentage_7d: float | None = None
    price_change_percentage_30d: float | None = None
    circulating_supply: float
    total_supply: float | None = None
    max_supply: float | None = None
    ath: float
    ath_change_percentage: float
    ath_date: str
    last_updated: str


class MarketData(BaseModel):
    total_market_cap: dict[str, float]
    total_volume: dict[str, float]
    market_cap_percentage: dict[str, float]
    active_cryptocurrencies: int
    markets: int
    market_cap_change_percentage_24h: float


class FearGreedIndex(BaseModel):
    value: int
    classification: str
    timestamp: str
    time_until_update: str | None = None


class FearGreedHistorical(BaseModel):
    value: int
    classification: str
    timestamp: str


class WhaleTransaction(BaseModel):
    hash: str
    from_address: str
    to_address: str
    value: float
    token_symbol: str
    token_decimal: int
    gas_used: float
    gas_price: float
    block_number: int
    timestamp: str


class DeFiProtocol(BaseModel):
    name: str
    slug: str
    category: str
    chain: str
    tvl: float
    change_1d: float | None = None
    change_7d: float | None = None
    mcap: float | None = None
    fdv: float | None = None
    url: str | None = None


class DeFiYield(BaseModel):
    pool: str
    project: str
    chain: str
    symbol: str
    tvlUsd: float
    apy: float
    apyBase: float | None = None
    apyReward: float | None = None
    rewardTokens: list[str] | None = None
    il7d: float | None = None
    apyPct7d: float | None = None


class GasEstimate(BaseModel):
    low: float
    average: float
    fast: float
    base_fee: float
    last_block: int


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
