# Nexus Synapse - The main LLM Server Application
import os
import torch
import time
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Optional

# --- Explicitly load the .env file from the script's directory ---
# This makes the script independent of the current working directory.
dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
# The MODEL_NAME is now reliably loaded from the .env file.
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt2")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Global Variables ---
model = None
tokenizer = None

# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    print("--- Starting Nexus Synapse LLM Server Node ---")
    print(f"Loading model: {MODEL_NAME} on device: {DEVICE}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(DEVICE) # type: ignore
        print("Model and tokenizer loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        raise e
    
    yield
    
    print("--- Shutting down Nexus Synapse LLM Server Node ---")

# --- FastAPI Application ---
app = FastAPI(title="Nexus Synapse - LLM Server", lifespan=lifespan)

# --- Pydantic Models ---
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7

class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatCompletionChoice]

# --- API Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    if not model or not tokenizer:
        raise HTTPException(status_code=503, detail="Model not loaded")

    prompt = request.messages[-1].content

    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    outputs = model.generate(
        **inputs,
        max_new_tokens=request.max_tokens,
        temperature=request.temperature,
        pad_token_id=tokenizer.eos_token_id
    )
    response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    response = ChatCompletionResponse(
        id="chatcmpl-123",
        object="chat.completion",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=Message(role="assistant", content=response_text),
                finish_reason="stop"
            )
        ]
    )
    return response

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "owned_by": "user",
                "permission": []
            }
        ]
    }