from CustomLLM.trainer.data_fetcher import *
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from decouple import AutoConfig, config
# from airflow.decorators import task, dag
from pymongo import MongoClient
from datetime import datetime
from tempfile import TemporaryDirectory, NamedTemporaryFile
from CustomLLM.trainer.model_trainer import *
from peft import LoraConfig
from CustomLLM.libs.blob import BlobStore, BlobStoreConfig, BlobStoreType
import logging
import shutil
from pathlib import Path
from dataclasses import dataclass
import json
import os
import argparse
import time

config = AutoConfig()
CONFIG_DATETIME_FORMAT = "%Y%m%dT%H%M%S"
AIRFLOW_XCOM_PATH=config("AIRFLOW_XCOM_PATH")


logger = logging.getLogger(__name__)

def _get_mongodb_client() -> MongoClient:
    password = config("MONGODB_PASSWORD")
    uri = f"mongodb+srv://kkundalia:{password}@customllm.zdxzipc.mongodb.net"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))

    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        logger.exception('Failed to connect to mongodb')
        raise e
    return client

def _get_blob_store_client() -> BlobStore:
    config = AutoConfig()
    blob_type = BlobStoreType(config('BLOB_TYPE'))
    if blob_type == BlobStoreType.LOCAL:
        config = BlobStoreConfig(blob_type, base_dir=config("BLOB_BASE_DIR"))
        return BlobStore(config)
    elif blob_type == BlobStoreType.AZURE:
        config = BlobStoreConfig(blob_type, container_name=config("AZURE_CONTAINER_NAME"), connection_str=config("AZURE_BLOB_CONNECTION_STRING"))
        return BlobStore(config)
    else:
        raise NotImplementedError("Cloud blobs are yet to be implemented.")

@dataclass
class TrainModelPipelineConfig:
    execution_mode: str # Can be "k8s" or "local"
    execution_task: str # can be "fetch_data", "preprocess", "train"
    train_model_name: str # TRAIN_MODEL_NAME
    execution_timestamp: str # EXECUTION_TIMESTAMP
    subreddit: str # SUBREDDIT
    subreddit_flair: str # SUBREDDIT_FLAIR
    max_posts_to_fetch: int # MAX_POSTS_TO_FETCH
    max_comments_per_post_to_fetch: int # MAX_COMMENTES_PER_POST_TO_FETCH
    retrain_model_on_data_start_date: datetime # RETRAIN_MODEL_ON_DATA_START_DATE
    retrain_model_on_data_end_date: datetime # RETRAIN_MODEL_ON_DATA_END_DATE
    huggingface_base_model: str # HUGGINGFACE_BASE_MODEL
    huggingface_base_model_tokenizer: str # HUGGINGFACE_BASE_MODEL_TOKENIZER
    ratelimit_seconds: int = 300 # RATELIMIT_SECONDS
    subreddit_time_filter: str = 'week' # SUBREDDIT_TIME_FILTER


def fetch_reddit_data(pipeline_config: TrainModelPipelineConfig) -> int:
    config = AutoConfig()
    rd_config = RedditConfig(
        app_id = config("REDDIT_APP_ID"),
        secret= config("REDDIT_SECRET"),
        username= config("REDDIT_USER_NAME"),
        password= config("REDDIT_USER_PWD"), 
        app_name= config("REDDIT_APP_NAME"),
        ratelimit_seconds=300
    )

    sc_cfg = SubRedditSearchConfig( # @todo: can paramaterize these
        pipeline_config.subreddit, 
        pipeline_config.subreddit_flair,
        sort='new',
        time_filter=pipeline_config.subreddit_time_filter
    )

    print("Beginning to collect posts from Reddit")
    rf = RedditFetched(rd_config)
    posts = rf.fetch_posts_batch(sc_cfg, max_posts=pipeline_config.max_posts_to_fetch, max_comments=pipeline_config.max_comments_per_post_to_fetch)
    print(f"Fetched {len(posts)}.")

    mongodb_client = _get_mongodb_client()
    db = config("MONGODB_DB")
    coll = config("MONGODB_COLLECTION")

    print("Beginning to insert to DB")
    successful_insertions = insert_to_db(mongodb_client, db, coll, posts)
    print(f"Inserted {successful_insertions} posts.")
    with open(AIRFLOW_XCOM_PATH, 'w+') as f:
        json.dump(successful_insertions, f)
    # @todo: XCOMs are dict, this returns a str. This is inconsistent. Make the XCOM and the return values the same
    return successful_insertions

def preprocessing(inserted_posts: int, pipeline_config: TrainModelPipelineConfig):
    # if not inserted_posts:
    #     raise Exception("nothing to fetch")
    config = AutoConfig()
    mongodb_client = _get_mongodb_client()
    db = config("MONGODB_DB")
    coll = config("MONGODB_COLLECTION")
    start_date = pipeline_config.retrain_model_on_data_start_date
    end_date = pipeline_config.retrain_model_on_data_end_date

    print(f"Fetching posts...")
    temp_dir = TemporaryDirectory()
    with TemporaryDirectory() as temp_dir:
        print("starting preprocessing")
        written_files = preprocess(mongodb_client, db, coll, start_date, end_date, temp_dir)
        if not written_files:
            raise Exception("No filtered files found for the time range. Can't finetune model")
        blobstore = _get_blob_store_client()
        blob_dest = blobstore.zip_and_write_folder(temp_dir, ["data", pipeline_config.execution_timestamp], "data") # @todo replace the actual execution run date
        with open(AIRFLOW_XCOM_PATH, 'w+') as f:
            json.dump(blob_dest, f)
        # @todo: This is inconsistent. Make the XCOM and the return values the same
        return blob_dest

def train_model_task(data_blob_dest: str, pipeline_config: TrainModelPipelineConfig):
    blobstore = _get_blob_store_client()
    logger.warning(f"starting to train model with {data_blob_dest}")
    with TemporaryDirectory() as tdr:
        zip_file = blobstore.get_file(data_blob_dest, tdr)
        shutil.unpack_archive(zip_file, tdr)
        data_files: List[str] = [i.as_posix() for i in Path(tdr).rglob("*.json")]

        peft_config = LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        logger.warning("starting to train model")
        save_model_dir = os.path.join(tdr, "model1")
        config = TrainerCofig(data_files, base_model=pipeline_config.huggingface_base_model, tokenizer=pipeline_config.huggingface_base_model_tokenizer, lora_config=peft_config, save_model_dir=save_model_dir)
        model_dir = train_model(config=config)
        print("uploading model to blob")
        result = blobstore.zip_and_write_folder(model_dir, ["models", pipeline_config.execution_timestamp], pipeline_config.train_model_name) # @todo replace "execution_run" with the pipeline execution time 
        with open(AIRFLOW_XCOM_PATH, 'w+') as f:
            json.dump(result, f)
        return result

def pipeline(pipeline_config: TrainModelPipelineConfig, kwargs: dict = None):
    if pipeline_config.execution_task == "fetch_data":
        return fetch_reddit_data(pipeline_config)
    elif pipeline_config.execution_task == "preprocess":
        if pipeline_config.execution_mode == "local":
            inserted_posts = kwargs.get("inserted_posts")
            if not inserted_posts:
                raise Exception("Need number {'inserted_posts': int} to run preprocess pipeline step for local execution mode")
        else:
            inserted_posts = os.environ["INSERTED_RECORDS"]
        print(f"---------- Inserted records are {inserted_posts}")
        return preprocessing(inserted_posts, pipeline_config)
    elif pipeline_config.execution_task == "train":
        if pipeline_config.execution_mode == "local":
            data_blob_dest = kwargs.get("data_blob_dest")
            if not data_blob_dest:
                raise Exception("Need {'data_blob_dest': str} to run train_model_task step the for local execution mode")
        else:
            data_blob_dest = os.environ["DATA_BLOB_DEST"]
        # time.sleep(100000)
        return train_model_task(data_blob_dest, pipeline_config)
    elif pipeline_config.execution_task == "all":
        fetched_posts = fetch_reddit_data(pipeline_config)
        data_file = preprocessing(fetched_posts, pipeline_config)
        return train_model_task(data_file, pipeline_config)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Script with execution mode and task arguments.')

    # Define command-line arguments
    parser.add_argument('--execution_mode', choices=['local', 'k8s'], help='Execution mode (local or k8s)', required=True)
    parser.add_argument('--execution_task', choices=["fetch_data", "preprocess", "train", "all"], type=str, help='Execution task', required=True)
    parser.add_argument('--kwargs', type=json.loads, required=False)

    # Parse command-line arguments
    args = parser.parse_args()

    # Access the values of the arguments
    execution_mode = args.execution_mode
    execution_task = args.execution_task
    kwargs = args.kwargs

    pipeline_config = TrainModelPipelineConfig(
        execution_mode = execution_mode,
        execution_task=execution_task, 
        train_model_name = config("TRAIN_MODEL_NAME"),
        execution_timestamp = config("EXECUTION_TIMESTAMP"),
        subreddit = config("SUBREDDIT"),
        subreddit_flair = config("SUBREDDIT_FLAIR"),
        max_posts_to_fetch=int(config("MAX_POSTS_TO_FETCH")),
        max_comments_per_post_to_fetch=int(config("MAX_COMMENTES_PER_POST_TO_FETCH")),
        retrain_model_on_data_start_date = datetime.strptime(config("RETRAIN_MODEL_ON_DATA_START_DATE"), CONFIG_DATETIME_FORMAT),
        retrain_model_on_data_end_date = datetime.strptime(config("RETRAIN_MODEL_ON_DATA_END_DATE"), CONFIG_DATETIME_FORMAT),
        huggingface_base_model = config("HUGGINGFACE_BASE_MODEL"),
        huggingface_base_model_tokenizer = config("HUGGINGFACE_BASE_MODEL_TOKENIZER"),
        ratelimit_seconds = int(config("RATELIMIT_SECONDS")),
        subreddit_time_filter = config("SUBREDDIT_TIME_FILTER")
    )

    print(execution_task, execution_mode, kwargs)

    pipeline(pipeline_config, kwargs)
