

```python
#Python-Reddit API Wrapper
import praw 
from psaw import PushshiftAPI

#for connecting to databases
import psycopg2
from sqlalchemy import create_engine

import pandas as pd
import datetime as dt
import numpy as np
import json #for parsing the return from the Google API
import urllib #for passing info to the Google API

import accesses #local file with API certs and database passwords.
```

### Create Connections to Reddit, PushShift, and PostGres Database


```python
# Creat a connection and cursor directly to the database using psycopg2.
conn = psycopg2.connect(host="localhost",database="reddit", user=accesses.db_user, 
                        password=accesses.db_pw)
c = conn.cursor()
```


```python
# Use this to rollback the cursor as neccessary.
# Keep commented out unless needed.
#conn.rollback()
```


```python
# Create the API credential variables using the local accesses file, and use those
# to create an instance of Reddit using the Python-Reddit API Wrapper (PRAW).

client_id=accesses.client_id
client_secret=accesses.client_secret
user_agent=accesses.user_agent

reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent=user_agent)

# Test the Reddit instance.  Should return 'True'.
print(reddit.read_only)
```

    True



```python
from psaw import PushshiftAPI
# use the reddit instance created with PRAW to connect to PushshiftAPI
api = PushshiftAPI(reddit)
```

### Scrape all Reddit IDs from Hiking using PushShift


```python
# Use this code to download all submission IDs from January 2017 to October 2019
start_epoch=int(dt.datetime(2017, 1, 1).timestamp())
end_epoch=int(dt.datetime(2019, 10, 1).timestamp())

# Save all results from the API to a list.  This is usually fast (less than 10 mins)
# So I did not write a database commit.  Additionally, the PushShift API only allows
# batch searching.
submission_results = list(api.search_submissions(after=start_epoch,before=end_epoch,
                                     subreddit='hiking'))
```


```python
# this will save off the Reddit Ids into a csv if we need them later.
submission_results_df = pd.DataFrame(submission_results)
submission_results_df.to_csv('{}_to_{}.csv'.fomrat(start_epoch, end_epoch))
```

### Use Reddit API to get information from each Reddit ID, and save to database


```python
# Create "raw_reddit" table in the "reddit" database.
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS public.raw_reddit
(
    id serial,
    reddit_id text,
    title text,
    score int, 
    num_comments int,
    int_time int,
    dt_time timestamp
);""")
conn.commit()
c.close()
```


```python
# for each reddit ID in the list of results, use the reddit API to get the
# title, score, num_comments, int_time (default returned by reddit) and the
# converted day time.
c = conn.cursor()
sql_insert = """INSERT INTO raw_reddit(reddit_id, title, score, num_comments, 
int_time, dt_time) VALUES(%s,%s,%s,%s,%s,%s)"""  

for s in submission_results:
    try:
        reddit_id = s.id
        title = praw.models.Submission(reddit,id=s.id).title
        score = praw.models.Submission(reddit,id=s.id).score
        num_comments = praw.models.Submission(reddit, id=s.id).score
        int_time = praw.models.Submission(reddit, id=s.id).created
        dt_time = dt.datetime.utcfromtimestamp(int_time)
        c.execute(sql_insert, (reddit_id,title,score,num_comments,int_time,dt_time))
        conn.commit()
        #print(reddit_id,title,score,num_comments,int_time,dt_time)
    except:
        print('Oops, failure')
        print(s.id)
c.close()
```


```python
# Drops the raw_reddit table.  
# DO NOT RUN THIS UNLESS YOU WANT TO RE-SCRAPE REDDIT!!!

#c.execute("""DROP table public.raw_reddit;""")
#conn.commit()
```

### Retrieve all reddit posts and assocated data from database, and condition it for GoogleMaps API


```python
c = conn.cursor()
df_raw_reddit_full = pd.read_sql('select * from raw_reddit', conn, index_col='id')
df_raw_reddit = df_raw_reddit_full.drop_duplicates('title')
c.close()
```

To identify place names, we will use a regular expression to find likely place names. This regular expression first looks for a non-capture group 

-beginning with a capital letter

-followed by one or more word element

-followed by zero or more periods (for abbreviations)

-followed by zero or more commas (since commas are often used to separate address pieces)

-followed by zero or more spaces

-followed by zero or more line breaks
and then captures whenever two or more of these patterns are identified.  There are several weaknesses with this approach.  First, place names that are not consistently capitalized like "Mount vernon, Virginia" will not be captured.  Additionally, many foreign place names such as "Playa del Mar" are not captured.  Many non-English words also negatively impact the Google API.  However, this simple approach is highly successful against the data at hand which is usually well-structured and consistent.


```python
pat_1 = r'((?:[A-Z]\w+\.*,*\s*\n*){2,})'

places = df_raw_reddit['title'].str.extractall(pat_1).unstack()
# to return the first element, the dataframe
places = places[0]
places = places.rename(columns = {0:'extracted_0',1:'extracted_1'})
places = pd.merge(df_raw_reddit, places, how='left', left_index=True,
                      right_index=True)

```


```python
# The API expects no spaces and words concatanated with a '+', which 
# is what this function does.
def convert_address(address):
    converted_address = ''
    try: 
        for word in address.split():
            converted_address += (word + '+')        
        return converted_address[:-1]
    except:
        pass
```


```python
places['converted_0'] = places['extracted_0'].apply(convert_address)
places['converted_1'] = places['extracted_1'].apply(convert_address)
places = places.replace({None:np.nan})
```

### Example of using GoogleMap API 

The API is accessed by passing the below url, the API key, and the converted address together.  The result is a variable length JSON object.  As shown below, we can use a dictionary to store the most relevenat metadata into an easily parsable object, no matter the length of the JSON object.


```python
address = 'George+Washington+University'
api_key = accesses.google_api
url = 'https://maps.googleapis.com/maps/api/geocode/json?'
url_address_api = '{}address={}&key={}'.format(url, address, api_key)

geo_dict = {}
geo_dict['address'] = address
try:
    with urllib.request.urlopen(url_address_api) as response: 
        js = json.loads(response.read())
    geo_dict['lat'] = js['results'][0]['geometry']['location']['lat']
    geo_dict['lon'] = js['results'][0]['geometry']['location']['lng']
    for component in js['results'][0]['address_components']:
        geo_dict[component['types'][0]] = component['long_name']
    
except:
    print('Error in Geocoding.', address, ' not found.')
```


```python
js
```




    {'results': [{'address_components': [{'long_name': '2121',
         'short_name': '2121',
         'types': ['street_number']},
        {'long_name': 'I Street Northwest',
         'short_name': 'I St NW',
         'types': ['route']},
        {'long_name': 'Northwest Washington',
         'short_name': 'Northwest Washington',
         'types': ['neighborhood', 'political']},
        {'long_name': 'Washington',
         'short_name': 'Washington',
         'types': ['locality', 'political']},
        {'long_name': 'District of Columbia',
         'short_name': 'DC',
         'types': ['administrative_area_level_1', 'political']},
        {'long_name': 'United States',
         'short_name': 'US',
         'types': ['country', 'political']},
        {'long_name': '20052', 'short_name': '20052', 'types': ['postal_code']}],
       'formatted_address': '2121 I St NW, Washington, DC 20052, USA',
       'geometry': {'location': {'lat': 38.8997145, 'lng': -77.0485992},
        'location_type': 'ROOFTOP',
        'viewport': {'northeast': {'lat': 38.9010634802915,
          'lng': -77.04725021970849},
         'southwest': {'lat': 38.8983655197085, 'lng': -77.0499481802915}}},
       'place_id': 'ChIJpXo8DrG3t4kRCKgn3Bv0e9o',
       'plus_code': {'compound_code': 'VXX2+VH Washington, District of Columbia, United States',
        'global_code': '87C4VXX2+VH'},
       'types': ['establishment', 'point_of_interest', 'university']}],
     'status': 'OK'}




```python
geo_dict
```




    {'address': 'George+Washington+University',
     'lat': 38.8997145,
     'lon': -77.0485992,
     'street_number': '2121',
     'route': 'I Street Northwest',
     'neighborhood': 'Northwest Washington',
     'locality': 'Washington',
     'administrative_area_level_1': 'District of Columbia',
     'country': 'United States',
     'postal_code': '20052'}



So the goal is to see if we can find a way to do this for everything.  The problem is that 'address components' is variable.  In some responses, there are only two components.  In otheres there are five.  Additionally, the different levels repersent different elements depending on where the location is. 

### Use the conditioned data from the title as an input to Google's Geocoding API to return coordinates and location metadata.  

Because we are using the free tier of Google's API, we can only process 40,000 geocodings a month.  Therefore, we will want to save every successful call into the database in its raw form so we do not have to get it back from the API.


```python
# Create "geocoded_addresses" table in the "reddit" database.
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS public.geocoded_addresses
(
    id int,
    results json
);""")
conn.commit()
c.close
```


```python
# Drops the geocoded_addresses table.  
# Keep commented out.
#c = conn.cursor()
#c.execute("""DROP table public.geocoded_addresses;""")
#conn.commit()
#c.close
```


```python
#function to check highest row:
def find_start(table_name, conn=conn):
    c = conn.cursor()
    query = "select max(id) from {}".format(table_name)
    c.execute(query)
    start = (c.fetchone()[0])
    c.close
    if start == None:
        start = 0
    return start
```


```python
def geocode_to_db(df, chunk_size):
    
    sql_insert_geocode = """INSERT INTO geocoded_addresses(id, results) VALUES(%s,%s)"""  
    api_key = accesses.google_api
    url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    
    start = find_start('geocoded_addresses')
    end = start + chunk_size
    # If the end of the chunk is greater than the index (accessed here as 'name') of 
    # the last element in the dataframe, use the last element's index as the endpoint.
    # this will prevent 'out of range' errors while ensureing we geocode all data available.
    if end > places.iloc[-1].name:
        end = places.iloc[-1].name
    print("Will start processing at loc {}.  Will End processing at {}".format(start, end))
    
    for name, row in df[start:end].iterrows():
        c = conn.cursor()
        address = row[0] 
        uid = name # unique id
        try:
            if pd.notna(address): 
                url_address_api = '{}address={}&key={}'.format(url, address, api_key)
                
                with urllib.request.urlopen(url_address_api) as response: 
                    js = (json.loads(response.read()))
                # Depsite multiple attempts, I had to load the JSON from the API and 
                # then dump it back into the PostGRES database.  When I tried to write
                # the JSON directly to the database, I kept getting errors.
                c.execute(sql_insert_geocode, (uid, json.dumps(js))) 
                conn.commit()
                print('Success! ID: ', uid)
                
            else: print('Row was blank.  Continuing.  ID: ', uid)
        except: print('Error in geocoding.  ID: ', uid)
        c.close()
```


```python
geocode_to_db((converted['converted_0'].to_frame()))
```
