# HuggingFace API Models Reference

## Available Free Models for Legal Analysis

### Llama Models (Meta)
```bash
# Llama 3.2 3B Instruct (Recommended - Fast & Good)
"hf_api_model": "meta-llama/Llama-3.2-3B-Instruct"

# Llama 3.2 1B Instruct (Fastest)
"hf_api_model": "meta-llama/Llama-3.2-1B-Instruct" 

# Llama 3.1 8B Instruct (Slower but more capable)
"hf_api_model": "meta-llama/Llama-3.1-8B-Instruct"
```

### Gemma Models (Google)
```bash
# Gemma 2 2B Instruct (Fast & Efficient)
"hf_api_model": "google/gemma-2-2b-it"

# Gemma 2 9B Instruct (More capable)
"hf_api_model": "google/gemma-2-9b-it"
```

### DeepSeek Models
```bash
# DeepSeek Coder V2 Lite (Good for structured analysis)
"hf_api_model": "deepseek-ai/deepseek-coder-6.7b-instruct"

# DeepSeek LLM 7B Chat
"hf_api_model": "deepseek-ai/deepseek-llm-7b-chat"
```

### Qwen Models (Alibaba)
```bash
# Qwen 2.5 3B Instruct (Fast & Good)
"hf_api_model": "Qwen/Qwen2.5-3B-Instruct"

# Qwen 2.5 7B Instruct
"hf_api_model": "Qwen/Qwen2.5-7B-Instruct"
```

### Mistral Models
```bash
# Mistral 7B Instruct v0.3
"hf_api_model": "mistralai/Mistral-7B-Instruct-v0.3"

# Mistral Nemo Instruct 2407 (12B)
"hf_api_model": "mistralai/Mistral-Nemo-Instruct-2407"
```

## How to Switch Models

### Option 1: Via API
```powershell
$config = @{
    model_type = 'hf_api'
    hf_api_model = 'meta-llama/Llama-3.2-3B-Instruct'
    hf_api_max_tokens = 1000
} | ConvertTo-Json

Invoke-RestMethod -Method Put -Uri http://127.0.0.1:8000/config -Body $config -ContentType 'application/json'
```

### Option 2: Edit config.json directly
```json
{
  "model_type": "hf_api",
  "hf_api_model": "google/gemma-2-2b-it",
  "hf_api_max_tokens": 1000
}
```

## Performance Recommendations

- **Fastest**: Llama-3.2-1B-Instruct, Gemma-2-2b-it
- **Best Balance**: Llama-3.2-3B-Instruct, Qwen2.5-3B-Instruct  
- **Most Capable**: Llama-3.1-8B-Instruct, Gemma-2-9b-it, Qwen2.5-7B-Instruct

## Notes

- All models are free via HuggingFace Inference API
- Your HUGGINGFACEHUB_API_TOKEN is already configured
- Models provide detailed legal analysis in the same format as Gemini
- Switch between models instantly without restarting the server
