from __future__ import print_function
from airflow.operators.python_operator import PythonOperator
from airflow.models import DAG
from datetime import datetime, timedelta

from pprint import pprint

from scraper.yahoo import run_scraper

today = datetime.today().replace(hour=20, minute=0, second=0) - timedelta(days=1)

args = {
    'owner': 'airflow',
    'start_date': today,
    'email': ['mailo.shawn@gmail.com'],
    'email_on_failure': True,
}

dag = DAG(
    dag_id='yahoo_scraper',
    default_args=args,
    catchup=False,
    schedule_interval='0 20 * * 1-5')


def scrape_yahoo(ds, **kwargs):
    pprint(kwargs)
    print(ds)
    run_scraper()
    return 'Yahoo Scraper DAG Finished Successfully'


task = PythonOperator(
    task_id='scrape_yahoo_finance',
    provide_context=True,
    python_callable=scrape_yahoo,
    dag=dag)
