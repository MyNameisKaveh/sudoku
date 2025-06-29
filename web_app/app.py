import os
from flask import Flask, jsonify, request, session, render_template
import sys

# Add the parent directory to the Python path to access sudoku_bot
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sudoku_bot.game_logic.sudoku import generate_puzzle, check_win as check_sudoku_win, solve_sudoku, is_valid_move, SIDE

from whitenoise import WhiteNoise

app = Flask(__name__, template_folder='templates', static_folder='static')
# It's crucial to set a secret key for session management
# Read from environment variable for production, with a fallback for local development
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key_123!@#')
# IMPORTANT: The fallback key is for local development ONLY.
# Set FLASK_SECRET_KEY in your production environment (e.g., Hugging Face Space secrets).

# Serve static files efficiently in production using WhiteNoise
# WhiteNoise will automatically find your static files if static_folder is set correctly
app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(os.path.dirname(__file__), 'static'))
# Add prefix for static files if they are not at root (e.g. /static/css/style.css)
# app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(os.path.dirname(__file__), 'static'), prefix='static/')
# However, Flask's default static_url_path is '/static', so WhiteNoise should work correctly
# with the default static serving if files are in 'web_app/static' and accessed via url_for.
# The most robust way for WhiteNoise to pick up Flask's static files is to let it wrap the app
# and it will use Flask's static_folder and static_url_path.
# Let's simplify the WhiteNoise setup assuming default Flask static handling.
# app.wsgi_app = WhiteNoise(app.wsgi_app)
# WhiteNoise should automatically use app.static_folder.
# If static_folder is 'static' (relative to app.py location), it's usually fine.
# The Flask app's static_folder is 'static', relative to the app's root path (where app.py is).
# So, web_app/static/ should be found by WhiteNoise.
# The following configuration is standard and should work:
# It tells WhiteNoise to serve files from the app's static_folder
# (which is 'static' relative to app.py, so web_app/static/)
# at the URL specified by app.static_url_path (default is '/static').
app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(os.path.dirname(__file__), 'static'))
# No, this is not quite right. WhiteNoise's `root` is for *all* files if you are not using add_files.
# The recommended way for Flask is simpler:
# app.wsgi_app = WhiteNoise(app.wsgi_app)
# app.wsgi_app.add_files(os.path.join(os.path.dirname(__file__), 'static'), prefix='static/')
# Flask's default static_url_path is 'static'.
# `static_folder` is 'static' relative to `app.py`.
# The most straightforward way:
app.wsgi_app = WhiteNoise(app.wsgi_app)
app.wsgi_app.add_files(os.path.join(os.path.dirname(__file__), 'static'), prefix=app.static_url_path)


# --- Helper Functions ---
def get_user_game():
    """Retrieves game state from session."""
    return {
        'puzzle_board': session.get('puzzle_board'),
        'solution_board': session.get('solution_board'),
        'current_board': session.get('current_board'),
        'difficulty': session.get('difficulty')
    }

def set_user_game(puzzle, solution, current, difficulty):
    """Saves game state to session."""
    session['puzzle_board'] = puzzle
    session['solution_board'] = solution
    session['current_board'] = current
    session['difficulty'] = difficulty
    session['game_active'] = True

def clear_user_game():
    """Clears game state from session."""
    session.pop('puzzle_board', None)
    session.pop('solution_board', None)
    session.pop('current_board', None)
    session.pop('difficulty', None)
    session.pop('game_active', False)

# --- API Routes ---

@app.route('/api/new_game', methods=['POST'])
def new_game_api():
    data = request.get_json()
    difficulty = data.get('difficulty', 'easy').lower()
    if difficulty not in ['easy', 'medium', 'hard']:
        difficulty = 'easy'

    try:
        puzzle, solution = generate_puzzle(difficulty)
        current_board_copy = [row[:] for row in puzzle] # User will modify this
        set_user_game(puzzle, solution, current_board_copy, difficulty)

        return jsonify({
            'message': f'New game started with difficulty: {difficulty}',
            'puzzle_board': puzzle,
            'current_board': current_board_copy, # Send initial state
            'difficulty': difficulty
        }), 200
    except Exception as e:
        print(f"Error generating puzzle: {e}") # Log error
        return jsonify({'error': 'Could not start new game. ' + str(e)}), 500

@app.route('/api/fill_cell', methods=['POST'])
def fill_cell_api():
    if not session.get('game_active'):
        return jsonify({'error': 'No active game. Start a new game first.'}), 400

    data = request.get_json()
    row = data.get('row')
    col = data.get('col')
    num = data.get('num')

    game_state = get_user_game()
    current_board = game_state.get('current_board')
    puzzle_board = game_state.get('puzzle_board')

    if current_board is None or puzzle_board is None:
         return jsonify({'error': 'Game state not found in session.'}), 500

    if not (isinstance(row, int) and isinstance(col, int) and isinstance(num, int) and \
            0 <= row < SIDE and 0 <= col < SIDE and 0 <= num <= SIDE): # num can be 0 to clear
        return jsonify({'error': 'Invalid input. Row/col must be 0-8, num must be 0-9 (0 to clear).'}), 400

    # Check if the cell is part of the original puzzle
    if puzzle_board[row][col] != 0:
        return jsonify({'error': 'Cannot change pre-filled numbers of the puzzle.'}), 400

    current_board[row][col] = num
    session['current_board'] = current_board # Update session

    return jsonify({
        'message': f'Cell ({row+1}, {col+1}) updated to {num if num != 0 else "empty"}.',
        'current_board': current_board
    }), 200

@app.route('/api/check_game', methods=['GET'])
def check_game_api():
    if not session.get('game_active'):
        return jsonify({'error': 'No active game.'}), 400

    game_state = get_user_game()
    current_board = game_state.get('current_board')
    solution_board = game_state.get('solution_board')

    if current_board is None or solution_board is None:
         return jsonify({'error': 'Game state not found in session.'}), 500

    is_filled = all(all(cell != 0 for cell in row) for row in current_board)
    is_correct = check_sudoku_win(current_board, solution_board)

    if is_correct:
        return jsonify({
            'is_solved': True,
            'is_filled': True,
            'message': 'تبریک! شما سودوکو را حل کردید!'
        }), 200
    else:
        return jsonify({
            'is_solved': False,
            'is_filled': is_filled,
            'message': 'جدول فعلی (هنوز) یک راه‌حل صحیح نیست.' if is_filled else 'جدول هنوز کامل نشده یا دارای خطا است.'
        }), 200


@app.route('/api/solve_game', methods=['GET'])
def solve_game_api():
    if not session.get('game_active'):
        return jsonify({'error': 'No active game.'}), 400

    game_state = get_user_game()
    solution_board = game_state.get('solution_board')

    if solution_board is None:
        return jsonify({'error': 'Solution not found in session.'}), 500

    # Update current board in session to the solution
    session['current_board'] = [row[:] for row in solution_board]

    return jsonify({
        'message': 'Showing solution.',
        'current_board': solution_board # Send the solved board
        }), 200

@app.route('/api/hint', methods=['GET'])
def hint_api():
    if not session.get('game_active'):
        return jsonify({'error': 'No active game.'}), 400

    game_state = get_user_game()
    current_board = game_state.get('current_board')
    solution_board = game_state.get('solution_board')

    if current_board is None or solution_board is None:
        return jsonify({'error': 'Game state not found in session.'}), 500

    empty_cells = []
    for r_idx in range(SIDE):
        for c_idx in range(SIDE):
            if current_board[r_idx][c_idx] == 0:
                empty_cells.append({'row': r_idx, 'col': c_idx})

    if not empty_cells:
        return jsonify({'message': 'Board is already full! No hints available.', 'hint': None, 'current_board': current_board}), 200

    import random
    hint_cell_info = random.choice(empty_cells)
    row, col = hint_cell_info['row'], hint_cell_info['col']
    hint_value = solution_board[row][col]

    current_board[row][col] = hint_value
    session['current_board'] = current_board

    return jsonify({
        'message': f'راهنمایی: مقدار خانه ({row+1}, {col+1}) عدد {hint_value} است.',
        'hint': {'row': row, 'col': col, 'value': hint_value},
        'current_board': current_board
    }), 200


# --- Route for serving the main HTML page ---
@app.route('/')
def index():
    return render_template('index.html') # Will be created later

if __name__ == '__main__':
    app.run(debug=True, port=5001)
