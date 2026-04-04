"""
BigQuery 업로드 스크립트
========================
실행: python upload_to_bq.py

CSV 파일을 BigQuery에 자동으로 덮어쓰기 업로드합니다.
"""

from google.cloud import bigquery
import os

PROJECT = 'ds-ysy'
DATASET = 'kakao_gift'
DIR     = os.path.dirname(os.path.abspath(__file__))

TABLES = [
    'users',
    'orders',
    'gift_receipts',
    'campaigns',
    'campaign_logs',
]

def upload():
    client = bigquery.Client(project=PROJECT)

    for table in TABLES:
        csv_path = os.path.join(DIR, f'{table}.csv')
        table_id = f'{PROJECT}.{DATASET}.{table}'

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,       # 헤더 스킵
            autodetect=True,           # 스키마 자동 감지
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # 덮어쓰기
        )

        print(f'업로드 중: {table}.csv → {table_id} ...', end=' ', flush=True)
        with open(csv_path, 'rb') as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
        job.result()  # 완료 대기
        print(f'완료 ({client.get_table(table_id).num_rows:,}행)')

    print('\n모든 테이블 업로드 완료!')

if __name__ == '__main__':
    upload()
