# ChatGPT-Clone

A ChatGPT-style AI chat web application with a Flask backend and a modern dark-themed UI. It integrates the DeepSeek API for intelligent responses, supports conversation management, and offers streaming-like response generation.

## Features

- **DeepSeek API Integration** – Leverages the DeepSeek API for generating conversational AI responses.
- **Conversation Management** – Create, view, and delete chat sessions to keep conversations organized.
- **Streaming-Like Responses** – Responses are delivered progressively to simulate real-time streaming.
- **Modern Dark-Themed UI** – A clean, responsive interface with a dark color scheme.
- **Persistent Chat History** – Conversations are stored in SQLite and retrieved on page reload.
- **RESTful API Backend** – Flask-based API with clear endpoints for chat and history management.

## Tech Stack

- Python
- Flask
- SQLite
- JavaScript
- HTML
- CSS
- DeepSeek API
- Gunicorn

## Installation

Follow these steps to set up the project locally.

### Prerequisites

- Python 3.8 or higher
- pip
- Git

### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/chatgpt-clone.git
   cd chatgpt-clone
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Copy the example environment file and fill in your own values.

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and provide the required keys (see [Environment Variables](#environment-variables)).

5. **Initialize the database**

   The SQLite database will be created automatically when the application runs for the first time.

6. **Run the application**

   For development:
   ```bash
   python app.py
   ```

   For production (using Gunicorn):
   ```bash
   gunicorn app:app
   ```

## Usage

Start the server and open your browser to `http://localhost:5000`.

### Basic Usage

1. Open the web interface.
2. Type a message in the input field and press Enter or click the send button.
3. The AI will respond progressively (streaming-like effect).
4. Use the conversation panel to switch between chats or start a new one.

### Example API Call (using curl)

Send a chat message to the API:

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what is AI?"}'
```

Expected response (streaming-like chunks or complete answer):

```json
{
  "response": "Artificial Intelligence (AI) refers to the simulation of human intelligence in machines..."
}
```

## Project Structure

```
├── app.py
├── ai_handler.py
├── database.py
├── config.py
├── requirements.txt
├── templates/index.html
├── static/css/style.css
├── static/js/chat.js
├── .env.example
├── .gitignore
```

- **app.py** – Main Flask application with routes and server startup.
- **ai_handler.py** – Handles communication with the DeepSeek API.
- **database.py** – SQLite database operations for storing conversations.
- **config.py** – Application configuration (e.g., reading environment variables).
- **requirements.txt** – Python dependencies.
- **templates/index.html** – Frontend HTML template.
- **static/css/style.css** – Stylesheet for the dark-themed UI.
- **static/js/chat.js** – Frontend JavaScript for chat interactions and streaming display.
- **.env.example** – Template for environment variables.
- **.gitignore** – Files and directories ignored by Git.

## API Endpoints

Based on the file structure, the application provides the following RESTful endpoints:

| Method | Endpoint            | Description                          |
|--------|---------------------|--------------------------------------|
| POST   | `/chat`             | Send a message and receive AI reply. |
| GET    | `/conversations`    | Retrieve list of all conversations.  |
| GET    | `/conversation/<id>`| Get messages for a specific conversation. |
| DELETE | `/conversation/<id>`| Delete a conversation.               |

*Note: Actual endpoints may vary; refer to `app.py` for precise routes.*

## Environment Variables

All required environment variables are listed in `.env.example`. Copy this file to `.env` and fill in the values.

| Variable         | Description                          |
|------------------|--------------------------------------|
| `DEEPSEEK_API_KEY` | Your DeepSeek API key.              |
| `SECRET_KEY`       | Flask secret key for session security. |
| `DATABASE_URL`     | (Optional) Path to SQLite database file (defaults to `chat.db`). |
| `FLASK_ENV`        | Set to `development` for debug mode. |

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Make your changes and commit them (`git commit -m 'Add YourFeature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a Pull Request.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.