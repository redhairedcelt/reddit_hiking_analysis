import pandas as pd
import accesses
import psycopg2
#%%
conn = psycopg2.connect(host="localhost",database="reddit", user=accesses.db_user, 
                        password=accesses.reddit_db_pw)
c = conn.cursor()

#%%
df = pd.read_sql('select * from hiking', conn)
df.head()