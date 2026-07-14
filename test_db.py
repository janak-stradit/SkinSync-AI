from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
import traceback

load_dotenv()
uri = os.environ.get('DATABASE_URL') or 'postgresql://postgres:postgres@localhost:5432/skinsync'
print('Using URI:', uri)
try:
    engine = create_engine(uri, connect_args={'connect_timeout':5})
    with engine.connect() as conn:
        print('SELECT 1 ->', conn.execute(text('SELECT 1')).scalar())
except Exception as e:
    print('Connection failed:')
    traceback.print_exc()
