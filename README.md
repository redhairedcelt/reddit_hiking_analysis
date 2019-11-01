# Analysis of Submissions to r/Hiking, January 2017 through September 2019

Welcome!  This is an analysis of Reddit's r/hiking subreddit from January 2017 through September 2019.  All analysis was conducted using Python 3.7 and PostGreSQL for data warehousing.  The code for this project is spread across three different Python Notebooks.


Click ![here](https://github.com/redhairedcelt/reddit_hiking_analysis/blob/master/post.png) 


<img src="https://github.com/redhairedcelt/reddit_hiking_analysis/blob/master/post.png" alt="hi" class="inline"/> for a high resolution map of all submissions in the continental US, colored by season and sized by total score.

## Scraping and Processing Data
[Link to notebook](https://redhairedcelt.github.io/reddit_hiking_analysis/Reddit_API_Scrape_Process.html)

I used the Python-Reddit API Wrapper (PRAW module) in conjuntion the PushShift API to scrape r/Hiking for all submissions from January 2017 to September 2019.  Because Reddit limits API pulls to 1,000, I couldnt use it to directly scrape the 40,000+ submissions.  The first step was to use PushShift to search for all Reddit IDs in r/Hiking during that time period, which were saved as csvs and in memory.  I then used the Reddit API to query each individual Reddit ID to get its title, number of upvotes (score), number of comments, and date published.  All information returned from Reddit was immediately stored in a PostGres database.

I then used regular expressions to extract likely place names, conditioned them for use with Google Maps geocoding API, and then passed all of them through the API.  Luckily, you can get 40,000 geocoding calls a month for free!  All of these calls returned JSON,  which was also stored in PostGres.

## Check Processing
[Link to notebook](https://redhairedcelt.github.io/reddit_hiking_analysis/Reddit_API_Check_Processing.html)

I wrote a separate script to ensure all Reddit IDs returned in the first phase were succsessfully passed through the geocoding API.  I had erronouesly assumed sequential returns when I had set up batch processing through the geocoding API, and had missed thousands of submissions.  This process acted as a unit test to ensure all submissions were processed.

## Analysis
[Link to notebook](https://redhairedcelt.github.io/reddit_hiking_analysis/Reddit_API_Analysis/Reddit_API_Analysis.html)

The main analysis of the data is located here.  I generated a wordcloud of the most frequent place names extracted from the submissions, examined outliers, looked at the distibution of upvotes and submissions over different years, months, and seasons, explored the loactions with the most submissions (California) and most upvotes (Washington state), plotted all submissions globally and across the US colored by season and sized by number of upvotes, and built choropleths globally and across the US colored by the density of submissions and by number of upvotes.

## Findings and Conclusions
Overall, the r/Hiking subreddit is increasing in popularity with more submissions and upvotes year over year since 2017.  There appears to be a significant bias toward the United States, and to a lesser extent Canada.  This is to be expected on an English lanaguage sub-reddit, but the scale of it was not anticipated.  

For geographic trends in the US, there is a high concentration across California, the state with the highest number of submissions and the third highest total score of upvotes.  However, Washington was remarkable for having the highest total score while ranking third on number of submissions.  This suggests that submissions featuring hiking destinations in Washington on average score higher than submissions from California.  There are also hotspots near concentrations of national parks and mountian ranges, as well as along coasts.

I analyzed seasonality to look for trends in both time and space for the four different seasons.  Overall, the summer and spring are more popular times for submissions.  However, I did not observe any strong trends spatially based on season.  A more detailed analysis of state by state totals and averages across the four season could identify unobserved trends.  Additionally, complete data for each season year over year would make this comparison more effective.

In conclusion, if you want a high scoring post on Reddit's r/Hiking, your best bet is to fly out to the Pacific Northwest and get some excellent photos of the beautiful scenery in the late Summer.  Judging from the wordcloud, submissions with "Park", "Lake", and "Trail" in the title have often appeared in the top 100.
