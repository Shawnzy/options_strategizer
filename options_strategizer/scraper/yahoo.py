import logging
import time
from datetime import datetime

import pandas as pd
import pytz
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import (
	DATE, INTEGER, MONEY, REAL, TIMESTAMP, VARCHAR
)
from yahoo_fin import options as yf_options


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TICKERS = ['nflx', 'aapl', 'voo']


class YahooDataDownloader:
	@classmethod
	def get_data(cls, tickers):
		logger.info('Yahoo Data Downloader Starting...')
		yahoo_data_ = {
			ticker: cls._get_ticker_options(ticker) for ticker in tickers
		}
		logger.info('Yahoo Data Downloader Finished Successfully')
		return yahoo_data_

	@classmethod
	def _get_ticker_options(cls, ticker):
		exp_dates = yf_options.get_expiration_dates(ticker)
		time.sleep(1)

		ticker_options = {
			exp_date: cls._get_options_for_expiration_date(ticker, exp_date)
			for exp_date in exp_dates
		}
		return ticker_options

	@classmethod
	def _get_options_for_expiration_date(cls, ticker, exp_date):
		logger.info(
			f'Getting options chain for {ticker} '
			f'options that expire on {exp_date}'
		)

		scraped_date = cls._get_scraped_date()
		chain = yf_options.get_options_chain(ticker, exp_date)
		time.sleep(1)

		chain['scraped_date'] = scraped_date
		return chain

	@staticmethod
	def _get_scraped_date():
		tz = pytz.timezone('EST')
		return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')


class YahooDataTransformer:
	@classmethod
	def transform_to_df(cls, data):
		logger.info(f'Yahoo Data Transformer Starting...')
		ticker_dfs = [
			cls._create_ticker_df(ticker, options)
			for ticker, options in data.items()
		]
		df = pd.concat(ticker_dfs)
		logger.info(f'Yahoo Data Transformer Finished Successfully')
		return df

	@classmethod
	def _create_ticker_df(cls, ticker, options):
		exp_date_dfs = [
			cls._create_ticker_exp_date_df(exp_date, chain)
			for exp_date, chain in options.items()
		]
		df = pd.concat(exp_date_dfs)
		df = df.assign(symbol=ticker)
		return df

	@classmethod
	def _create_ticker_exp_date_df(cls, exp_date, chain):
		df = cls._combine_calls_and_puts(chain)
		df = df.assign(expiration_date=exp_date)
		df = df.assign(scraped_date=chain['scraped_date'])
		return df

	@staticmethod
	def _combine_calls_and_puts(chain):
		df_call = chain['calls'].assign(option_type='call')
		df_put = chain['puts'].assign(option_type='put')
		return pd.concat([df_call, df_put])


class YahooDataDfFormatter:
	@classmethod
	def format(cls, df):
		logger.info(f'Yahoo Data Df Formatter Starting...')
		df = cls._format_columns(df)
		df = cls._format_expiration_date(df)
		df = cls._format_last_trade_date(df)
		df = cls._format_scraped_date(df)
		df = cls._format_percent_change(df)
		df = cls._format_implied_volatility(df)
		df = cls._format_numeric_columns(df)
		df = cls._index_df(df)
		logger.info(f'Yahoo Data Df Formatter Finished Successfully')
		return df

	@staticmethod
	def _format_columns(df):
		df.columns = df.columns.str.lower()\
			.str.replace(' ', '_')\
			.str.replace('%', 'percent')
		return df

	@staticmethod
	def _format_expiration_date(df):
		df.expiration_date = pd.to_datetime(df.expiration_date, errors='ignore')
		return df

	@staticmethod
	def _format_last_trade_date(df):
		df.last_trade_date = df.last_trade_date.str.replace('EDT', '')
		df.last_trade_date = pd.to_datetime(df.last_trade_date, errors='ignore')
		return df

	@staticmethod
	def _format_scraped_date(df):
		df.scraped_date = pd.to_datetime(df.scraped_date, errors='ignore')
		return df

	@staticmethod
	def _format_percent_change(df):
		df.percent_change = df.percent_change.str.replace(r'%', '')
		return df

	@staticmethod
	def _format_implied_volatility(df):
		df.implied_volatility = df.implied_volatility.str.replace(r'%', '')
		return df

	@staticmethod
	def _format_numeric_columns(df):
		cols = [
			'strike', 'last_price', 'bid', 'ask', 'change', 'percent_change',
			'volume', 'open_interest', 'implied_volatility'
		]
		df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
		return df

	@staticmethod
	def _index_df(df):
		df = df.set_index([
			'symbol', 'expiration_date', 'option_type', 'strike', 'scraped_date'
		])
		return df


class YahooDataDBHandler:
	index_cols = [
		'symbol', 'expiration_date', 'option_type', 'strike', 'scraped_date'
	]
	date_cols = ['last_trade_date', 'expiration_date', 'scraped_date']
	dtypes = {
		'contract_name': VARCHAR(),
		'last_trade_date': TIMESTAMP(),
		'strike': MONEY(),
		'last_price': MONEY(),
		'bid': MONEY(),
		'ask': MONEY(),
		'change': MONEY(),
		'percent_change': REAL(),
		'volume': INTEGER(),
		'open_interest': INTEGER(),
		'implied_volatility': REAL(),
		'option_type': VARCHAR(),
		'expiration_date': DATE(),
		'scraped_date': TIMESTAMP(),
		'symbol': VARCHAR(),
	}

	def __init__(self, db_string):
		self.conn = create_engine(db_string)

	def write(self, df, table_name, if_exists='append'):
		logger.info(f'Yahoo Data Df Upload to Database Starting...')
		df.to_sql(
			name=table_name,
			con=self.conn,
			if_exists=if_exists,
			index=True,
			dtype=self.dtypes
		)
		logger.info(f'Yahoo Data Df Upload to Database Finished Successfully')

	def read(self, table_name):
		df = pd.read_sql(
			f"SELECT * from {table_name}",
			con=self.conn,
			parse_dates=self.date_cols,
			index_col=self.index_cols
		)
		df.sort_index(inplace=True)
		return df


def run_scraper():
	yahoo_data = YahooDataDownloader.get_data(TICKERS)
	yahoo_data_df = YahooDataTransformer.transform_to_df(yahoo_data)
	formatted_yahoo_data_df = YahooDataDfFormatter.format(yahoo_data_df)
	uploader = YahooDataDBHandler("postgres://admin:secret@pgsql-server:5432/postgres")
	uploader.write(formatted_yahoo_data_df, 'test', if_exists='append')


if __name__ == "__main__":
	run_scraper()
