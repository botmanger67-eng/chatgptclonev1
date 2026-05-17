from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import os
import json
from typing import Dict, Any, Optional, Generator
from database import (
    init_db,
    get_conversations,
    get_messages,
    save_message,
    create_conversation,
    delete_conversation
)
from ai_handler import get_ai_stream_response, get_ai_complete_response
from config import SECRET_KEY, DATABASE_URL  # type: ignore

app = Flask(__name__)

# Secure configuration
app.config['SECRET_KEY'] = SECRET_KEY or os.urandom(24).hex()
app.config['DATABASE_URL'] = DATABASE_URL or 'sqlite:///chat.db'

# Initialize database on startup
with app.app_context():
    init_db()


@app.route('/')
def index() -> str:
    """Render the main chat interface."""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {'status': 'ok'}


@app.route('/api/conversations', methods=['GET'])
def list_conversations() -> Dict[str, Any]:
    """Return all conversations for the current session."""
    session_id = request.cookies.get('session_id') or 'default'
    try:
        conversations = get_conversations(session_id)
        return {'conversations': conversations, 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}, 500


@app.route('/api/conversations', methods=['POST'])
def new_conversation() -> Dict[str, Any]:
    """Create a new conversation and return its ID."""
    session_id = request.cookies.get('session_id') or 'default'
    try:
        conv_id = create_conversation(session_id)
        return {'conversation_id': conv_id, 'success': True}
    except Exception as e:
        return {'error': str(e), 'success': False}, 500


@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
def remove_conversation(conv_id: str) -> Dict[str, Any]:
    """Delete a conversation by ID."""
    session_id = request.cookies.get('session_id') or 'default'
    try:
        success = delete_conversation(conv_id, session_id)
        if success:
            return {'success': True}
        else:
            return {'error': 'Conversation not found', 'success': False}, 404
    except Exception as e:
        return {'error': str(e), 'success': False}, 500


@app.route('/api/chat', methods=['POST'])
def chat() -> Dict[str, Any]:
    """Send a message and receive a complete AI response (non-streaming)."""
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return {'error': 'Missing message field', 'success': False}, 400

    message = data['message'].strip()
    conversation_id = data.get('conversation_id')
    session_id = request.cookies.get('session_id') or 'default'

    if not message:
        return {'error': 'Message cannot be empty', 'success': False}, 400

    try:
        # Save user message
        save_message(conversation_id, 'user', message, session_id)

        # Retrieve conversation history
        messages = get_messages(conversation_id, session_id)

        # Get AI response
        ai_response = get_ai_complete_response(messages)

        # Save AI response
        save_message(conversation_id, 'assistant', ai_response, session_id)

        return {
            'response': ai_response,
            'conversation_id': conversation_id,
            'success': True
        }
    except Exception as e:
        return {'error': str(e), 'success': False}, 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream() -> Response:
    """Send a message and receive streaming AI response (Server-Sent Events)."""
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return jsonify({'error': 'Missing message field', 'success': False}), 400

    message = data['message'].strip()
    conversation_id = data.get('conversation_id')
    session_id = request.cookies.get('session_id') or 'default'

    if not message:
        return jsonify({'error': 'Message cannot be empty', 'success': False}), 400

    def generate() -> Generator[str, None, None]:
        try:
            # Save user message
            save_message(conversation_id, 'user', message, session_id)

            # Retrieve conversation history
            messages = get_messages(conversation_id, session_id)

            # Get stream from AI handler
            stream = get_ai_stream_response(messages)

            full_response = ""
            for chunk in stream:
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk})}\n\n"

            # Save the complete AI response
            save_message(conversation_id, 'assistant', full_response, session_id)

            # Signal end of stream
            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.errorhandler(404)
def not_found(error: Any) -> Dict[str, Any]:
    """Handle 404 errors."""
    return {'error': 'Resource not found', 'success': False}, 404


@app.errorhandler(500)
def internal_error(error: Any) -> Dict[str, Any]:
    """Handle 500 errors."""
    return {'error': 'Internal server error', 'success': False}, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')