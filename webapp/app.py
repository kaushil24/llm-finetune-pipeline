from flask import Flask, render_template, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import os
import re

app = Flask(__name__, template_folder="template")

@app.route('/')
def index():
    return render_template('chatv2.html')

@app.route('/generate', methods=['POST'])
def generate():
    """
    request format: {
    "prompt": str
    }
    """
    # Get the prompt from the request
    prompt = request.form['prompt']
    resp = generate_response(prompt)

    # Return the response as JSON
    return jsonify({'response': resp})

def generate_response(prompt_question):
    # Define the parameters for the OpenAI API call
    model_base_dir = "/Users/k2/SCU/Project/CustomLLM/blob/temp/test/financellm"
    model = AutoModelForCausalLM.from_pretrained(model_base_dir)
    with open(os.path.join(model_base_dir, "adapter_config.json")) as f_in:
        config = json.load(f_in)
    tokenizer = AutoTokenizer.from_pretrained(config["base_model_name_or_path"])
    max_length = 400
    prompt = f"### Question: {prompt_question}\n### Answer: "
    input_ids = tokenizer.encode(prompt, return_tensors="pt", add_special_tokens=True)
    generated_ids = model.generate(input_ids=input_ids, num_beams=2, max_length=max_length,  repetition_penalty=2.5, length_penalty=1.0, early_stopping=True)
    preds = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True) for g in generated_ids]
    res = preds[0]
    return re.search(r'### Answer:(.*)', res, re.DOTALL).group(0).replace("### Answer:", "")

if __name__ == '__main__':
    app.run(debug=True)
