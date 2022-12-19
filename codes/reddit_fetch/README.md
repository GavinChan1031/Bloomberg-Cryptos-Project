# reddit-maker
[toc]

## Getting Started
### Requirements
Required:
1. PRAW; 2. PMAW; 3. fastparquet; 4. tqdm; 5. click

```
pip install praw
pip install pmaw
pip install fastparquet
```

- PRAW: https://praw.readthedocs.io/en/stable/index.html
- PMAW: https://github.com/mattpodolak/pmaw
- fastparquet: https://fastparquet.readthedocs.io/en/latest/index.html

### Config
- Set save path and reddit api auth in ./rmaker/utils.py:
  ```python
  text_path = "./"  # The Place To Save Data

  reddit_auth = {
    "CLIENT_ID": "",
    "SECRET_TOKEN": "",
    "data": {
      "username": ""
    }
  }
  ```

- Set number of thread in ./rmaker/maker.py
  ```python
  # ... LINE 19
  class RedditMaker:
    NUM_WORKERS = 22  # Num Of Thread
  # ...
  ```
  Refering to PMAW's doc
  > When selecting the number of threads you can follow one of the two methodologies:
  Number of processors on the machine, multiplied by 5
  Minimum value of 32 and the number of processors plus 4

### Run reddit-maker
This package is designed to run in command line. But you can also import this package and call a specific function, which will be discussed in the later part.

- Download reddit posts
  ```
  python -m rmaker [start] [end] [channels]
  ```
  - [start], [end]: start/end dates yyyy-mm-dd
  - [channels]: list of subreddit channel, separate by comma
  
- Download reddit comments
  ```
  python -m rmaker -c [start] [end] [channels]
  ```
  - [start], [end]: start/end dates yyyy-mm-dd
  - [channels]: list of subreddit channel, separate by comma
  - **Make Sure** you have already downloaded the post of the subreddit selected in the given time range

## How reddit-maker works
### reddit api & pushshift
- **reddit api**
  - provides data of post & comment, and other funcs as well
  - but cannot search historical post/comment through it 
  - the historical data is accessible through id (its index)
  https://www.reddit.com/dev/api
- **pushshift**
  - does snap shot and saves
  - historical data search OK
  - but the data is not up to date
  - site is not stable
  
### PRAW & PMAW
- **PRAW**: a wrapper for reddit api
- **PMAW**: a multithread wrapper for pushshift api. PRAW connection is integrated.
  
### How reddit-maker works
- **Fetch Post**
  1. Fetch post data from pushshift
  2. Enrich with latest data from reddit api (through PMAW)
  3. Save fetched data
- **Fetch Comment**
  - Find all comments in one specific day
    - Similar to *Fetch Post*
    - Not recommended because of speed
    - If you want to do this, just use PMAW function directly without enrichment (reddit api is extremely slow)
  - Find comments of posts that submitted in one specific day
    1. Load ids of posts
    2. Search ids of comments in ~~pushshift~~(the endpoint is offline) reddit api
    3. Fetch comment data 
    4. Save

### Key Functions
- **`search_post(channel: str, start: int, end: int)`**
  Return a dataframe of post.
  - `channel: str` - list of subreddit channel, separate by comma
  - `start: int` - start timestamp
  - `end: int` - end timestamp
- **`search_comment(channel: str, start: int, end: int)`**
  Return a dataframe of comment.
  - `channel: str` - subreddit channel, separate by comma
  - `start: int` - start timestamp
  - `end: int` - end timestamp
- **`search_comment_by_post_r(post_ids: List[str])`**
  Search the comments of specified posts (solely from reddit api). Return a dataframe of comment.
  - `post_ids: List[str]` - a list of post id
- **`search_comment_by_post(post_ids: List[str])`**
  Search the comments of specified posts (through pushshift & reddit api). Return a dataframe of comment.
  ***NOTE** this func is not working currently due to the pushshift endpoint that this func relies on is offline*
  - `post_ids: List[str]` - a list of post id


## Trouble Shoot
### Pushshift is down
Pushshift is maintained by individuals and is not very stable. Sometimes it is down. If you are calling pushshift related funcs and find the reddit-maker is not working (no network activity / nothing fetched for a long time), check the pushshift status.
https://stats.uptimerobot.com/l8RZDu1gBG
https://www.reddit.com/r/pushshift/hot/
https://www.reddit.com/r/pushshift/comments/uw0hk7/mini_faq_before_posting_is_pushshift_down_please/
If pushshift is operational but the reddit-maker is not working, chances are that it is fetching too aggressively. Try to decrease `NUM_WORKERS`, increase `RATE_LIMIT`, increase `MAX_SLEEP`, or increase `BASE_BACKOFF`.

### Status Code 500 Error
It is likely caused by that the `id` is deleted by reddit. It can be solved by modifying PMAW a bit.

In PMAW package files, find ./Request.py. Add the following in import part
```python
from prawcore.exceptions import ServerError
```
In `class Request`, modify func `_enrich_data` a bit
```python
def _enrich_data(self):
    # create batch of fullnames up to 100
    fullnames = []
    while len(fullnames) < 100:
        try:
            fullnames.append(self.enrich_list.popleft())
        except IndexError:
            break
    
    # exit loop if nothing to enrich
    if len(fullnames) == 0:
        return
    
    try:
        # TODO: may need to change praw usage based on multithread performance
        resp_gen = self.praw.info(fullnames=fullnames)
        praw_data = [vars(obj) for obj in resp_gen]
        results = self._apply_filter(praw_data)
        self.resp.responses.extend(results)
        
    except RedditAPIException:
        self.enrich_list.extend(fullnames)
    ###### ADD FOLLOWING  ########
    except ServerError:  # added by yyr
        if len(fullnames) == 1:
            # print('x')
            return
        self._solve_500(fullnames)
```
Also in `class Request`, add two more func to handle 500 error
```python
def _solve_500_(self, fullnames):
    if len(fullnames) == 0:
        return
    try:
        resp_gen = self.praw.info(fullnames=fullnames)
        praw_data = [vars(obj) for obj in resp_gen]
        results = self._apply_filter(praw_data)
        self.resp.responses.extend(results)

    except RedditAPIException:
        self.enrich_list.extend(fullnames)
    except ServerError:
        if len(fullnames) == 1:
            # print('x')
            return
        self._solve_500(fullnames)

def _solve_500(self, fullnames):
    div = randint(1, len(fullnames)-1)
    fullnames_l = fullnames[:div]
    fullnames_r = fullnames[div:]

    self._solve_500_(fullnames_l)
    self._solve_500_(fullnames_r)
```
*P.S. this is not a very elegant way to solve this problem*

***NOTE** there may be other reason causing the code 500 error*