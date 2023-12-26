from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer
from datasets import load_dataset
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
from typing import List, Optional
from peft import LoraConfig
from dataclasses import dataclass

@dataclass
class TrainerCofig:
    data_files: List[str]
    save_model_dir: str
    base_model: str
    lora_config: LoraConfig
    tokenizer: Optional[str] = None


def train_model(config: TrainerCofig) -> str:
    dataset = load_dataset("json", data_files=config.data_files, split="train")
    model = AutoModelForCausalLM.from_pretrained(config.base_model)
    # tokenizer = AutoTokenizer.from_pretrained(config.base_model)

    def formatting_prompts_func(example):
        output_texts = []
        for i in range(len(example['question'])):
            text = f"### Question: {example['question'][i]}\n ### Answer: {example['answer'][i]}"
            output_texts.append(text)
        return output_texts

    # response_template = " ### Answer:"
    # collator = DataCollatorForCompletionOnlyLM(response_template, tokenizer=tokenizer)

    peft_config = config.lora_config

    trainer = SFTTrainer(
        model,
        train_dataset=dataset,
        formatting_func=formatting_prompts_func,
        # data_collator=collator,
        peft_config=peft_config
    )

    trainer.train()
    trainer.model.save_pretrained(config.save_model_dir)
    return config.save_model_dir
