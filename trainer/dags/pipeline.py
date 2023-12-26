from pendulum import datetime, duration
from datetime import timedelta
from airflow import DAG
from airflow.configuration import conf
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator
)
from airflow.operators.bash import BashOperator
from kubernetes.client import models as k8s
from decouple import AutoConfig

config = AutoConfig()

default_args = {
        "params": {
            # blob env vars
            "BLOB_TYPE": config("BLOB_TYPE"),
            "AZURE_BLOB_CONNECTION_STRING": config("AZURE_BLOB_CONNECTION_STRING"),
            "AZURE_CONTAINER_NAME": config("AZURE_CONTAINER_NAME"),
            # Pipeline config
            "TRAIN_MODEL_NAME": config("TRAIN_MODEL_NAME"),
            "EXECUTION_TIMESTAMP": "{{ ts_nodash }}",
            "SUBREDDIT": config("SUBREDDIT"),
            "SUBREDDIT_FLAIR": config("SUBREDDIT_FLAIR"),
            "MAX_POSTS_TO_FETCH": config("MAX_POSTS_TO_FETCH"),
            "MAX_COMMENTES_PER_POST_TO_FETCH": config("MAX_COMMENTES_PER_POST_TO_FETCH"),
            "RETRAIN_MODEL_ON_DATA_START_DATE": config("RETRAIN_MODEL_ON_DATA_START_DATE"),
            "RETRAIN_MODEL_ON_DATA_END_DATE": config("RETRAIN_MODEL_ON_DATA_END_DATE"),
            "HUGGINGFACE_BASE_MODEL": config("HUGGINGFACE_BASE_MODEL"),
            "HUGGINGFACE_BASE_MODEL_TOKENIZER": config("HUGGINGFACE_BASE_MODEL_TOKENIZER"),
            "RATELIMIT_SECONDS": config("RATELIMIT_SECONDS"),
            "SUBREDDIT_TIME_FILTER": config("SUBREDDIT_TIME_FILTER"),
            # airflow stuff
            "AIRFLOW_XCOM_PATH": "/airflow/xcom/return.json",
        }
    }

dag = DAG('model_trainer',schedule_interval=None, start_date=datetime(2023, 12, 12), default_args=default_args)

start = BashOperator(
    dag=dag,
    task_id="params_tester",
    bash_command="echo ---------{{ params.HUGGINGFACE_BASE_MODEL }}"
)

fetched_data = KubernetesPodOperator(
    dag=dag,
    task_id="fetch_data",
    image="customllmreg.azurecr.io/train_pipeline",
    image_pull_secrets=[k8s.V1LocalObjectReference("img-pull-sec-3")],
    do_xcom_push=True,
    env_vars={
        # secret keys
        "REDDIT_SECRET": config("REDDIT_SECRET"),
        "REDDIT_APP_ID": config("REDDIT_APP_ID"),
        "REDDIT_APP_NAME": config("REDDIT_APP_NAME"),
        "REDDIT_USER_NAME": config("REDDIT_USER_NAME"),
        "REDDIT_USER_PWD": config("REDDIT_USER_PWD"),
        "MONGODB_PASSWORD": config("MONGODB_PASSWORD"),
        "MONGODB_COLLECTION": config("MONGODB_COLLECTION"),
        "MONGODB_DB": config("MONGODB_DB"),
        # blob env vars
        "BLOB_TYPE": "{{ params.BLOB_TYPE }}",
        "AZURE_BLOB_CONNECTION_STRING": "{{ params.AZURE_BLOB_CONNECTION_STRING }}",
        "AZURE_CONTAINER_NAME": "{{ params.AZURE_CONTAINER_NAME }}",
        # Pipeline config
        "TRAIN_MODEL_NAME": "{{ params.TRAIN_MODEL_NAME }}",
        "EXECUTION_TIMESTAMP": "{{ ts_nodash }}",
        "SUBREDDIT": "{{ params.SUBREDDIT }}",
        "SUBREDDIT_FLAIR": "{{ params.SUBREDDIT_FLAIR }}",
        "MAX_POSTS_TO_FETCH": "{{ params.MAX_POSTS_TO_FETCH }}",
        "MAX_COMMENTES_PER_POST_TO_FETCH": "{{ params.MAX_COMMENTES_PER_POST_TO_FETCH }}",
        "RETRAIN_MODEL_ON_DATA_START_DATE": "{{ params.RETRAIN_MODEL_ON_DATA_START_DATE }}",
        "RETRAIN_MODEL_ON_DATA_END_DATE": "{{ params.RETRAIN_MODEL_ON_DATA_END_DATE }}",
        "HUGGINGFACE_BASE_MODEL": "{{ params.HUGGINGFACE_BASE_MODEL }}",
        "HUGGINGFACE_BASE_MODEL_TOKENIZER": "{{ params.HUGGINGFACE_BASE_MODEL_TOKENIZER }}",
        "RATELIMIT_SECONDS": "{{ params.RATELIMIT_SECONDS }}",
        "SUBREDDIT_TIME_FILTER": "{{ params.SUBREDDIT_TIME_FILTER }}",
        # airflow stuff
        "AIRFLOW_XCOM_PATH": "/airflow/xcom/return.json",
        # pipeline and task stuff
        "EXECUTION_TASK": "fetch_data",
        "EXECUTION_MODE": "k8s",
    }
)

preprocess_data = KubernetesPodOperator(
    dag=dag,
    task_id="preprocess_data",
    image="customllmreg.azurecr.io/train_pipeline",
    image_pull_secrets=[k8s.V1LocalObjectReference("img-pull-sec-3")],
    do_xcom_push=True,
    env_vars={
        # secret keys
        "REDDIT_SECRET": config("REDDIT_SECRET"),
        "REDDIT_APP_ID": config("REDDIT_APP_ID"),
        "REDDIT_APP_NAME": config("REDDIT_APP_NAME"),
        "REDDIT_USER_NAME": config("REDDIT_USER_NAME"),
        "REDDIT_USER_PWD": config("REDDIT_USER_PWD"),
        "MONGODB_PASSWORD": config("MONGODB_PASSWORD"),
        "MONGODB_COLLECTION": config("MONGODB_COLLECTION"),
        "MONGODB_DB": config("MONGODB_DB"),
        # blob env vars
        "BLOB_TYPE": "{{ params.BLOB_TYPE }}",
        "AZURE_BLOB_CONNECTION_STRING": "{{ params.AZURE_BLOB_CONNECTION_STRING }}",
        "AZURE_CONTAINER_NAME": "{{ params.AZURE_CONTAINER_NAME }}",
        # Pipeline config
        "TRAIN_MODEL_NAME": "{{ params.TRAIN_MODEL_NAME }}",
        "SUBREDDIT": "{{ params.SUBREDDIT }}",
        "SUBREDDIT_FLAIR": "{{ params.SUBREDDIT_FLAIR }}",
        "EXECUTION_TIMESTAMP": "{{ ts_nodash }}",
        "MAX_POSTS_TO_FETCH": "{{ params.MAX_POSTS_TO_FETCH }}",
        "MAX_COMMENTES_PER_POST_TO_FETCH": "{{ params.MAX_COMMENTES_PER_POST_TO_FETCH }}",
        "RETRAIN_MODEL_ON_DATA_START_DATE": "{{ params.RETRAIN_MODEL_ON_DATA_START_DATE }}",
        "RETRAIN_MODEL_ON_DATA_END_DATE": "{{ params.RETRAIN_MODEL_ON_DATA_END_DATE }}",
        "HUGGINGFACE_BASE_MODEL": "{{ params.HUGGINGFACE_BASE_MODEL }}",
        "HUGGINGFACE_BASE_MODEL_TOKENIZER": "{{ params.HUGGINGFACE_BASE_MODEL_TOKENIZER }}",
        "RATELIMIT_SECONDS": "{{ params.RATELIMIT_SECONDS }}",
        "SUBREDDIT_TIME_FILTER": "{{ params.SUBREDDIT_TIME_FILTER }}",
        # airflow stuff
        "AIRFLOW_XCOM_PATH": "/airflow/xcom/return.json",
        # pipeline and task stuff
        "EXECUTION_TASK": "preprocess",
        "EXECUTION_MODE": "k8s",
        "INSERTED_RECORDS": "{{ task_instance.xcom_pull(task_ids='fetch_data', key='return_value') }}"
    }
)
train_model = KubernetesPodOperator(
    dag=dag,
    task_id="train_model",
    image="customllmreg.azurecr.io/train_pipeline",
    image_pull_secrets=[k8s.V1LocalObjectReference("img-pull-sec-3")],
    # container_resources={
    #     'request_memory': '8Gi',
    #     'limit_memory': '12Gi',
    #     'request_cpu': '800m',
    #     'limit_cpu': '3000m',
    # },
    container_resources=k8s.V1ResourceRequirements(
        requests={
            'cpu': '2000m',
            'memory': '4Gi',
        },
        limits={
            'cpu': '3500m',
            'memory': '25Gi',
        },
    ),
    do_xcom_push=True,
    env_vars={
        # secret keys
        "REDDIT_SECRET": config("REDDIT_SECRET"),
        "REDDIT_APP_ID": config("REDDIT_APP_ID"),
        "REDDIT_APP_NAME": config("REDDIT_APP_NAME"),
        "REDDIT_USER_NAME": config("REDDIT_USER_NAME"),
        "REDDIT_USER_PWD": config("REDDIT_USER_PWD"),
        "MONGODB_PASSWORD": config("MONGODB_PASSWORD"),
        "MONGODB_COLLECTION": config("MONGODB_COLLECTION"),
        "MONGODB_DB": config("MONGODB_DB"),
        # blob env vars
        "BLOB_TYPE": "{{ params.BLOB_TYPE }}",
        "AZURE_BLOB_CONNECTION_STRING": "{{ params.AZURE_BLOB_CONNECTION_STRING }}",
        "AZURE_CONTAINER_NAME": "{{ params.AZURE_CONTAINER_NAME }}",
        # Pipeline config
        "TRAIN_MODEL_NAME": "{{ params.TRAIN_MODEL_NAME }}",
        "SUBREDDIT": "{{ params.SUBREDDIT }}",
        "SUBREDDIT_FLAIR": "{{ params.SUBREDDIT_FLAIR }}",
        "EXECUTION_TIMESTAMP": "{{ ts_nodash }}",
        "MAX_POSTS_TO_FETCH": "{{ params.MAX_POSTS_TO_FETCH }}",
        "MAX_COMMENTES_PER_POST_TO_FETCH": "{{ params.MAX_COMMENTES_PER_POST_TO_FETCH }}",
        "RETRAIN_MODEL_ON_DATA_START_DATE": "{{ params.RETRAIN_MODEL_ON_DATA_START_DATE }}",
        "RETRAIN_MODEL_ON_DATA_END_DATE": "{{ params.RETRAIN_MODEL_ON_DATA_END_DATE }}",
        "HUGGINGFACE_BASE_MODEL": "{{ params.HUGGINGFACE_BASE_MODEL }}",
        "HUGGINGFACE_BASE_MODEL_TOKENIZER": "{{ params.HUGGINGFACE_BASE_MODEL_TOKENIZER }}",
        "RATELIMIT_SECONDS": "{{ params.RATELIMIT_SECONDS }}",
        "SUBREDDIT_TIME_FILTER": "{{ params.SUBREDDIT_TIME_FILTER }}",
        # airflow stuff
        "AIRFLOW_XCOM_PATH": "/airflow/xcom/return.json",
        # pipeline and task stuff
        "EXECUTION_TASK": "train",
        "EXECUTION_MODE": "k8s",
        "DATA_BLOB_DEST": "{{ task_instance.xcom_pull(task_ids='preprocess_data', key='return_value') }}"
    }
)


start >> fetched_data >> preprocess_data
preprocess_data >> train_model

# dag.test()
# docker build . -t customllm_airflow -f trainer/Dockerfile.airflow; docker tag docker.io/library/customllm_airflow  customllmreg.azurecr.io/customllm_airflow; docker push customllmreg.azurecr.io/customllm_airflow
# docker build . -t train_pipeline -f trainer/Dockerfile; docker tag docker.io/library/train_pipeline  customllmreg.azurecr.io/train_pipeline; docker push customllmreg.azurecr.io/train_pipeline