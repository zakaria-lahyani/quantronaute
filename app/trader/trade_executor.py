from app.utils.config import LoadEnvironmentVariables


class TradeExecutor:
    def __init__(self, mode: str, config:LoadEnvironmentVariables, **kwargs):
        self.mode = mode
        self.DAILY_LOSS_LIMIT = config.DAILY_LOSS_LIMIT
        self.TRADER_IS_UP = True

        # self.trade_restriction = TradeRestriction(
        #     restriction_path=config.RESTRICTION_CONF_FOLDER_PATH,
        #     default_close_time_str=config.DEFAULT_CLOSE_TIME,
        #     news_duration=config.NEWS_RESTRICTION_DURATION,
        #     market_close_duration=config.MARKET_CLOSE_RESTRICTION_DURATION
        # )
        #
        # if mode == 'live':
        #     if 'endpoints' not in kwargs:
        #         raise ValueError("Live trading requires endpoints")
        #     self.trader = LiveTrader(kwargs['endpoints'])
        # elif mode == 'backtest':
        #     if 'journal_db' not in kwargs:
        #         raise ValueError("Backtest requires journal_db")
        #     self.trader = SimTrader( kwargs['journal_db'], kwargs['indicators'])
        # else:
        #     raise ValueError(f"Invalid trading mode: {mode}")
