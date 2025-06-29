import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

from config import BOT_TOKEN, DEFAULT_DIFFICULTY
from game_logic.sudoku import generate_puzzle, check_win, print_board_to_console, SIDE

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store current game state (In-memory, will be replaced by DB or more robust solution later)
# context.user_data is a dict that can be used to store data per user.
# We will store:
# context.user_data['puzzle'] -> the initial puzzle board (immutable for the current game)
# context.user_data['solution'] -> the solution to the current puzzle (immutable)
# context.user_data['current_board'] -> the board as the user fills it (mutable)
# context.user_data['game_active'] -> boolean, True if a game is in progress

# --- Helper function to display board ---
def format_board_html(board: list[list[int]], original_puzzle: list[list[int]] = None) -> str:
    """Formats the Sudoku board as an HTML string for display in Telegram."""
    em_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    # For empty cells, use a different marker, e.g., a blank space or a dot.
    # Using a zero-width space for empty cells to maintain alignment.
    empty_cell_char = "▫️" # "⬜️" # alternately " . " or " _ "

    s = "<pre>"
    # s += "╔═══╤═══╤═══╦═══╤═══╤═══╦═══╤═══╤═══╗\n" # Top border
    s += "╔═══════════╦═══════════╦═══════════╗\n" # Top border
    for i, row in enumerate(board):
        if i > 0 and i % 3 == 0:
            # s += "╠═══╪═══╪═══╬═══╪═══╪═══╬═══╪═══╪═══╣\n" # Row separator
            s += "╠═══════════╬═══════════╬═══════════╣\n" # Row separator

        s += "║ " # Left border of row
        for j, num in enumerate(row):
            if j > 0 and j % 3 == 0:
                s += "║ " # Column block separator

            display_num = str(num) if num != 0 else empty_cell_char

            if original_puzzle and original_puzzle[i][j] != 0: # It's a pre-filled number
                s += f"<b>{display_num}</b> "
            elif num != 0: # User filled number
                s += f"<i>{display_num}</i> "
            else: # Empty cell
                s += f"{empty_cell_char} "

        s += "║\n" # Right border of row
    # s += "╚═══╧═══╧═══╩═══╧═══╧═══╩═══╧═══╧═══╝\n" # Bottom border
    s += "╚═══════════╩═══════════╩═══════════╝\n" # Bottom border
    s += "</pre>"
    return s

async def display_current_board(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str = None):
    """Helper function to display the current board to the user."""
    if not context.user_data.get('game_active', False):
        await update.message.reply_text("هنوز بازی‌ای شروع نشده! با /new_game یک بازی جدید شروع کن.")
        return

    board_str = format_board_html(context.user_data['current_board'], context.user_data['puzzle'])

    # TODO: Add inline keyboard for numbers 1-9 and a "Clear" button for input
    # For now, just display the board

    full_message = ""
    if message_text:
        full_message += message_text + "\n\n"
    full_message += board_str

    await update.message.reply_html(full_message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and clears any existing game state for the user."""
    user = update.effective_user
    await update.message.reply_html(
        rf"سلام {user.mention_html()} عزیز! 👋 خوش اومدی به ربات سودوکو.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(
        "برای شروع یک بازی جدید، دستور /new_game رو بفرست.\n"
        "می‌تونی سطح سختی رو هم مشخص کنی، مثلا: /new_game easy (سطوح: easy, medium, hard)\n\n"
        "پس از شروع بازی، برای وارد کردن عدد از دستور زیر استفاده کن:\n"
        "/fill <ردیف> <ستون> <عدد>\n"
        "مثلا: /fill 1 1 5 (عدد 5 را در ردیف 1، ستون 1 قرار می‌دهد)\n"
        "ردیف و ستون از 1 تا 9 هستند.\n"
        "برای پاک کردن یک خانه: /fill <ردیف> <ستون> 0\n\n"
        "برای بررسی وضعیت فعلی: /check\n"
        "برای دیدن جدول: /board"
    )
    # Clear any previous game data for this user
    context.user_data.clear()
    context.user_data['game_active'] = False


async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts a new Sudoku game."""
    difficulty = DEFAULT_DIFFICULTY
    if context.args:
        chosen_difficulty = context.args[0].lower()
        if chosen_difficulty in ["easy", "medium", "hard"]:
            difficulty = chosen_difficulty
        else:
            await update.message.reply_text(f"سطح سختی '{chosen_difficulty}' نامعتبره. از 'easy', 'medium', یا 'hard' استفاده کن. بازی با سطح {DEFAULT_DIFFICULTY} شروع میشه.")

    try:
        logger.info(f"User {update.effective_user.id} starting new game with difficulty: {difficulty}")
        puzzle, solution = generate_puzzle(difficulty)

        context.user_data['puzzle'] = puzzle
        context.user_data['solution'] = solution
        context.user_data['current_board'] = [row[:] for row in puzzle] # Make a mutable copy for the user to play
        context.user_data['game_active'] = True
        context.user_data['difficulty'] = difficulty

        logger.info(f"Game generated for user {update.effective_user.id}. Puzzle displayed below (debug).")
        # print_board_to_console(puzzle) # Debugging
        # print_board_to_console(solution) # Debugging

        await update.message.reply_text(f"بازی جدید با سطح سختی '{difficulty}' شروع شد!")
        await display_current_board(update, context)
        await update.message.reply_text("برای وارد کردن عدد: /fill <ردیف> <ستون> <عدد> (مثلا: /fill 1 1 5)")

    except Exception as e:
        logger.error(f"Error generating puzzle for difficulty {difficulty}: {e}", exc_info=True)
        await update.message.reply_text("متاسفانه مشکلی در تولید پازل پیش اومد. لطفا دوباره امتحان کن.")
        context.user_data['game_active'] = False


async def board_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the current Sudoku board."""
    if not context.user_data.get('game_active', False):
        await update.message.reply_text("هنوز بازی‌ای شروع نشده! با /new_game یک بازی جدید شروع کن.")
        return
    await display_current_board(update, context, "جدول فعلی شما:")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    help_text = (
        "دستورات موجود:\n"
        "/start - شروع کار با ربات و نمایش راهنما\n"
        "/new_game [difficulty] - شروع بازی جدید سودوکو.\n"
        "  سطوح سختی موجود: easy, medium, hard (مثال: `/new_game medium`)\n"
        "  اگر سطح سختی مشخص نشود، از 'easy' استفاده می‌شود.\n"
        "/fill <ردیف> <ستون> <عدد> - قرار دادن یک عدد در خانه مشخص شده.\n"
        "  ردیف و ستون باید بین 1 تا 9 باشند.\n"
        "  عدد باید بین 1 تا 9 باشد. برای پاک کردن یک خانه از عدد 0 استفاده کنید.\n"
        "  مثال: `/fill 1 1 5` (عدد 5 در ردیف اول، ستون اول)\n"
        "  مثال پاک کردن: `/fill 1 1 0`\n"
        "/board - نمایش جدول فعلی بازی.\n"
        "/check - بررسی اینکه آیا جدول فعلی به درستی حل شده است.\n"
        "/hint - (هنوز پیاده‌سازی نشده) دریافت راهنمایی.\n"
        "/solve - (هنوز پیاده‌سازی نشده) نمایش راه‌حل کامل بازی (بازی فعلی تمام می‌شود).\n"
        "/help - نمایش این پیام راهنما."
    )
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN_V2 # اطمینان از اینکه از پارس مود مناسب استفاده می‌شود اگر در help_text از مارک‌داون استفاده شده باشد
    )

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new_game", new_game))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("board", board_command))
    # application.add_handler(CommandHandler("fill", fill_command)) # To be added next
    # application.add_handler(CommandHandler("check", check_command)) # To be added next


    # Run the bot until the user presses Ctrl-C
    logger.info("Sudoku Bot is starting...")
    application.run_polling()
    logger.info("Bot has stopped.")

if __name__ == "__main__":
    main()
