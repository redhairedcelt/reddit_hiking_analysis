import psycopg2
import praw
import accesses #local file with API certs and database passwords.

#%%
# First connect to the database and create a cursor.
conn = psycopg2.connect(host="localhost",database="reddit", 
                        user=accesses.db_user, 
                        password=accesses.reddit_db_pw)
c = conn.cursor()
print('conn and cursor created successfully.')
#%%

# Create "hiking" table in the "reddit" database.
c.execute("""CREATE TABLE IF NOT EXISTS public.hiking
(
    id serial,
    title text 
);""")
conn.commit()


#%%
# Create the API creds variables using the local accesses file, and use those
# to create an instance of Reddit using the Python-Reddit API Wrapper (PRAW).

client_id=accesses.client_id
client_secret=accesses.client_secret
user_agent=accesses.user_agent

reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent=user_agent)

# Test the Reddit instance.  Should return 'True'.
print(reddit.read_only)
#%%
# Test the Reddit instance is working and returns the top 5 posts in r/Hiking.
for submission in reddit.subreddit('hiking').top(limit=5):
    print(submission.id)

#%%
# Scrape the top 1000 posts in r/Hiking and update each one in the table.
sql_insert = """INSERT INTO hiking(title) VALUES(%s)"""  

for submission in reddit.subreddit('hiking').top():
    text = submission.title
    c.execute(sql_insert, (text,))
    
conn.commit()


#%%
# Test the database update.
c.execute('select * from hiking;')
rows = c.fetchall()
for row in rows:
    print(row)

#%%
# Close the connection.
conn.close()
