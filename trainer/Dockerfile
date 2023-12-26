FROM python:3.9.8-slim

WORKDIR /app/CustomLLM

COPY trainer/requirements.txt .

RUN pip install --upgrade pip && pip install -r /app/CustomLLM/requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:/app"
RUN mkdir -p /app/CustomLLM/trainer
RUN mkdir -p /app/CustomLLM/libs
RUN mkdir -p /app/CustomLLM/tmp/blob
COPY libs /app/CustomLLM/libs
COPY trainer /app/CustomLLM/trainer

CMD ["sh", "-c", "python trainer/model_trainer_pipeline.py --execution_mode ${EXECUTION_MODE} --execution_task ${EXECUTION_TASK} "]
