

```python
import pandas as pd
import numpy as np
import re #for extracting place names from titles

import accesses #local file with API certs and database passwords.

#for connecting to databases
import psycopg2
from sqlalchemy import create_engine

import json #for parsing the return from the Google API
import urllib #for passing info to the Google API
```

## How well did our code work at extracting, converting and geocoding our locations?

I had to pull the data in multiple batches, and not all of the data was returned sequentially by PushShift's API.  Therefore, I'll make sure that every unique ID that was scraped from Reddit that was successfully extracted and converted through my processes was passed to the GoogleMaps API.  We'll then run through this notebook one more time to ensure every unique ID is accounted for.  I also updated the code to update a NULL value into the database if geocoding failed so that we could track them as well.

## Rebuild raw_reddit, extracted, converted, and geocoded dataframes for analysis


```python
# Creat a connection and cursor directly to the database using psycopg2.
conn = psycopg2.connect(host="localhost",database="reddit", user=accesses.db_user, 
                        password=accesses.db_pw)
c = conn.cursor()
```


```python
c = conn.cursor()
df_raw_reddit = pd.read_sql('select * from raw_reddit', conn, index_col='id')
c.close()
```


```python
pat_1 = r'((?:[A-Z]\w+\.*,*\s*\n*){2,})'

df_extracted = df_raw_reddit['title'].str.extractall(pat_1).unstack()
# to return the first element, the dataframe
df_extracted = df_extracted[0]
df_extracted = df_extracted.rename(columns = {0:'extracted_0',1:'extracted_1',
                                  2:'extracted_2',3:'extracted_3',
                                  4:'extracted_4'})
places = pd.merge(df_raw_reddit, df_extracted, how='left', left_index=True,
                      right_index=True)
```


```python
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


```python
# During testing, multiple runs introduced several duplicates.  Since this
# class focuses on Python, I handled the duplicates here rather than in 
# the database itself.

c = conn.cursor()
# select all rows from the geocoded_addresses table
df_geocoded = pd.read_sql('select * from geocoded_addresses', conn)
# get original length
print(len(df_geocoded))
# drop all duplicates by ID and set index to the id
df_geocoded.drop_duplicates('id', inplace=True)
df_geocoded.set_index('id', inplace=True)
# print length to see how many we removed
print(len(df_geocoded))
c.close()
```

    33979
    33952



```python
def build_geo_dict(df):
    geo_dict_list = []
    error_list = {}
    for row in df.iterrows():
        uid = row[0]
        data = (row[1][0])
        geo_dict = {}
        geo_dict['id'] = uid
        
        try:
            geo_dict['lat'] = data['results'][0]['geometry']['location']['lat']
            geo_dict['lon'] = data['results'][0]['geometry']['location']['lng']
            for component in data['results'][0]['address_components']:
                geo_dict[component['types'][0]] = component['long_name']
            geo_dict_list.append(geo_dict)
        
        except: 
            error_list[uid]=data
        
    return (geo_dict_list, error_list)
```


```python
results, errors = build_geo_dict(df_geocoded)
```


```python
final_full = pd.DataFrame(results)
final_full.set_index('id', inplace=True)
```


```python
merged = pd.merge(final_full, places, right_index=True, left_index=True, how='left')
```


```python
final = merged[['country','administrative_area_level_1', 'score', 'title', 'extracted_0',
                'dt_time','lat', 'lon']]
```

## Summary


```python
print('Rows scraped from reddit:', len(df_raw_reddit))
print('Rows extracted by RegEx:', len(df_extracted))
print('Rows from geocoded table:', len(df_geocoded))
print('Rows geocoded accurately:', len(results))
print('Rows with geocoding errors', len(errors))
print('Rows in final df:', len(final_full))
```

    Rows scraped from reddit: 43900
    Rows extracted by RegEx: 33952
    Rows from geocoded table: 33952
    Rows geocoded accurately: 30940
    Rows with geocoding errors 3012
    Rows in final df: 30940


## Are all the rows extracted from the RegEx in the Geocoded table?

There were originally thousands of rows that were successfully extracted from the raw reddit titles but had not been successfully geocoded.  To make sure we processed all of our locations, we will take the index of all the successful extractions, iterate through each one and see if that index is in the geocoded index, and if it is not we will add it to a new list called 'missing_ids'.  We'll create a new dataframe from the original places dataframe using the 'missing_ids' to subset the full dataframe.  

This new dataframe has just the ids that were successfully extracted and converted, but never geocoded.  We can now run our geocoding function against these ids.  We'll also use an updated function that writes None to the database if the GoogleMaps API rejects it, which we weren't doing in the first scrape.  This will ensure that future run-throughs of the process wont keep on trying to run the same places through the API that cause errors.  We'll capture all of these errors in our geo_dict building funtion.


```python
extracted_index = df_extracted.index
geocoded_index = df_geocoded.index
```


```python
missing_ids=[]
for i in extracted_index:
    if i not in geocoded_index:
        missing_ids.append(i)
```


```python
reprocessing = places.loc[missing_ids,]
```


```python
len(reprocessing)
```




    0



## Reprocess Tracks


```python
def geocode_to_db(df):
    
    sql_insert_geocode = """INSERT INTO geocoded_addresses(id, results) VALUES(%s,%s)"""  
    sql_insert_error = """INSERT INTO geocoded_addresses(id, results) VALUES(%s,%s)"""  
    api_key = accesses.google_api
    url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    
    #start = find_start('geocoded_addresses')
    #end = start + chunk_size
    # If the end of the chunk is greater than the index (accessed here as 'name') of 
    # the last element in the dataframe, use the last element's index as the endpoint.
    # this will prevent 'out of range' errors while ensureing we geocode all data available.
    #if end > places.iloc[-1].name:
    #    end = places.iloc[-1].name
    #print("Will start processing at loc {}.  Will End processing at {}".format(start, end))
    
    for name, row in df.iterrows():
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
        except: 
            c.execute(sql_insert_error, (uid,  None,))
            print('Error in geocoding.  ID: ', uid)
        c.close()
```


```python
geocode_to_db(reprocessing['converted_0'].to_frame())
```
