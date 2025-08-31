# Synapse
Synapse is a self-hosted, on-premises generative AI server designed for privacy, control, and performance. It provides an OpenAI-compatible API, allowing any application that works with the OpenAI API to seamlessly connect to open-source Large Language Models (LLMs) running on your own hardware.

**Please note:** Synapse is an early-stages prototype whichs currently lacks any form of authentication or security and is only for research purposes. Do not implement this in a production environment without first hardening the server.

## Core Features
- Privacy First: All models and data remain on your private server or cloud. No data is ever sent to third-party services.

- OpenAI-Compatible API: A drop-in replacement for the OpenAI API. Any tool, library, or application built to use api.openai.com can be pointed to Synapse with minimal changes.

- Bring Your Own Model (BYOM): Easily configure the server to run any open-source model from the Hugging Face Hub, from small models like gpt2 to powerful ones like Gemma 2.

- Scalable & High-Availability: Built with a load balancer to distribute traffic across multiple AI server nodes, enabling horizontal scaling and failover for production workloads.

- Cost-Effective: Leverage your own hardware to avoid expensive, usage-based API costs from proprietary model providers.

## Architecture Overview
Synapse consists of two primary components:

1. AI Server Node (main.py): A FastAPI application responsible for loading a specified LLM from Hugging Face and exposing it via an OpenAI-compatible /v1/chat/completions endpoint. You can run multiple instances of this node.
2. Load Balancer (load_balancer.py): A smart reverse proxy that sits in front of the AI Server Nodes. It distributes incoming API requests in a round-robin fashion and performs regular health checks, automatically removing unresponsive nodes from the pool.

## Getting Started
Follow these instructions to set up and run Synapse on your local machine.

### Prerequisites
- Python 3.10+
- Git
- A <a href="https://huggingface.co/" target="_blank">Hugging Face</a> account (for downloading gated models like Gemma 2).

### 1. Installation
First, clone the repository and set up the Python environment.
```
# Clone the repository (if you haven't already)
# git clone [https://github.com/YourUsername/synapse.git](https://github.com/YourUsername/synapse.git)
# cd synapse

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install the required Python packages
pip install -r requirements.txt
```

### 2. Configuration
Configuration is managed through a .env file.

1. Create the .env file: Create a file named .env in the root of the project.
2. Set the Model: Add the MODEL_NAME variable to specify which model from the Hugging Face Hub to use. For example:
```
# .env
MODEL_NAME="google/gemma-2-2b-it"
```
3. Authenticate with Hugging Face: If you are using a gated model (like Gemma or Llama), you must log in to your Hugging Face account via the command line.
```
huggingface-cli login
# Paste your "read" access token when prompted.
```

### 3. Running the Application
You need to run the AI server nodes and the load balancer in separate terminals.

1. Start the AI Server Nodes: Open three separate terminals, activate the virtual environment in each, and run the following command (using a different port for each). The first time you run this, it will download the model, which may take several minutes.
```
# Terminal 1
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2
uvicorn main:app --host 0.0.0.0 --port 8001

# Terminal 3
uvicorn main:app --host 0.0.0.0 --port 8002
```
2. Start the Load Balancer: Open a fourth terminal, activate the environment, and run:
```
# Terminal 4
uvicorn load_balancer:app --host 0.0.0.0 --port 5000
```
The load balancer will start and confirm that it has found the healthy server nodes. Your API is now live at http://localhost:5000.

### Usage Example
You can interact with the API using any tool that can make HTTP requests. Here is an example using curl in the Windows Command Prompt:
```
curl -X POST http://localhost:5000/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\": \"google/gemma-2-2b-it\", \"messages\": [{\"role\": \"user\", \"content\": \"Explain how a transformer model works in one sentence.\"}]}"
```

## Contributing
Contributions are welcome! If you'd like to contribute to Synapse, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature (git checkout -b feature/AmazingFeature).
3. Commit your changes (git commit -m 'Add some AmazingFeature').
4. Push to the branch (git push origin feature/AmazingFeature).
5. Open a Pull Request.

Please open an issue first to discuss what you would like to change.