from dataclasses import  dataclass
import praw
from datetime import datetime, timedelta
from decouple import config
from typing import List, Dict, Optional, Union, Any, Tuple
from praw.models import Submission, Comment
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, BulkWriteError
from pymongo.results import InsertOneResult
from praw.models import ListingGenerator
from datetime import datetime, time
import json
import os
import logging

logger = logging.getLogger(__name__)

@dataclass
class RedditConfig:
    app_id: str
    secret: str
    username: str
    password: str
    app_name: str
    ratelimit_seconds: str

@dataclass
class SubRedditSearchConfig:
    subreddit: str
    flair: Optional[str] = None
    sort: Optional[str] = 'new'
    time_filter: Optional[str] = 'day'
    syntax: Optional[str] = 'lucene'

class RedditFetched:

    def __init__(self, config: RedditConfig):
        self.reddit = praw.Reddit(
            client_id = config.app_id,
            client_secret = config.secret,
            username = config.username,
            password = config.password,
            user_agent = config.app_name,
            ratelimit_seconds = config.ratelimit_seconds,
        )

    def fetch_posts_batch(self, search_config: SubRedditSearchConfig, max_posts: int = 100, max_comments: int = 20) -> List[Dict[str, str]]:
        """
        Returns a list of dict:
        [{ 
            "reddit_id": str,
            "title": str,
            "author_name": "str",
            "url": str,
            "created_at": str,
            "comments": [{
                "author":str,
                "body": str,
                "upvotes": int,
                "replies": int,
        }]
        Fetches max_posts number of posts
        """
        print("Starting to fetch posts")
        subreddit = self.reddit.subreddit(search_config.subreddit)
        fetched_posts: ListingGenerator = subreddit.search( # <- is a Generator
            f'flair:{search_config.flair}',
            sort=search_config.sort,
            time_filter=search_config.time_filter,
            syntax=search_config.syntax
        )
        fetched_posts.limit = max_posts

        posts: List[Dict[str, str]] = []
        post: Submission = None
        for post in fetched_posts:
            post_dict =  {
                    "reddit_id": post.id,
                    "title": post.title,
                    "author_name": post.author.name,
                    "body": post.selftext,
                    "url": post.url,
                    "created_at": datetime.utcfromtimestamp(post.created_utc),
                    "comments": []
            }
            max_comments = max_comments if max_comments <= len(post.comments) else len(post.comments)
            comments = []
            for i in range(max_comments):
                try:
                    cmt = post.comments[i]
                    comments.append({
                    "author": cmt.author.name, 
                    "body": cmt.body,
                    "upvotes": cmt.score,
                    "replies": len(cmt.replies)
                    })
                except Exception as e:
                    logging.warning(f"Failed to fetch a comment for {post.id}")
            posts.append(post_dict)
        print(f'Fetched {len(posts)} from Reddit.')
        return posts

def insert_to_db(client: MongoClient, db_name: str, collection_name: str, data: Dict[Any, Any]) -> int:
    """
    Nothing shabby, just dumps a bunch of data to mongodb cluster one at a time. Returns total number of successfully inserted documents.
    Returns how many were successfully inserted.
    """
    print(f"Beginnig to insert posts to Db")
    db = client[db_name]
    collection = db[collection_name]
    inserted = 0

    for d in data:
        try:
            collection.insert_one(d)
            inserted+=1
        except DuplicateKeyError as e:
            logger.warning(f"Failed to insert data DuplicateKeyError. Skipping this row")
    print(f"Inserted {inserted} posts to db")
    return inserted


def preprocess(client: MongoClient, db_name: str, collection_name: str, start_date: datetime, end_date: datetime, source_dir: str):
    """
    Loads data from db, preprocesses (converts in the form of question, answer json) and saves to jsons in data dir
    It will create one json file for each date. It will only write those posts that have > 0 comments
    """
    print(f"Beginning pre-processing....")
    MAX_ANS_PER_QUES = 5
    db = client[db_name]
    collection = db[collection_name]
    current_date = start_date

    written_files = []
    # Loop through each day between start and end dates
    print(f"Starting to fetch data from {start_date}-{end_date}.")
    while current_date <= end_date:
        # Format the date to use in the filename
        formatted_date = current_date.strftime("%Y-%m-%d")
 
        query = {
            "created_at": {"$gte": current_date, "$lt": (current_date + timedelta(days=1))}
        }

        fetched_posts = list(collection.find(query))
        print(f"Fetched {len(fetched_posts)} for {current_date} ")

        # filters only those posts that have comments (aka answers) in them
        filtered_posts = []
        for post in fetched_posts:
            question = f"{post.get('title')}\n{post.get('body')}"
            max_ans = min(MAX_ANS_PER_QUES, len(post.get("comments")))
            for i in range(max_ans):
                filtered_posts.append({"question": question, "answer": post.get('comments')[i].get("body")})

        # write down the filtered posts
        if filtered_posts:
            filename = f"{formatted_date}.json"

            file_path = os.path.join(source_dir, filename)

            with open(file_path, "w") as json_file:
                json.dump(filtered_posts, json_file, default=str, indent=2)
            written_files.append(file_path)

        # Move to the next day
        current_date += timedelta(days=1)

    print(f"Preprocessed {len(written_files)} and stored to {source_dir}")
    return written_files
