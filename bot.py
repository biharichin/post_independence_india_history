
import os
import re
import telegram
import logging

# --- Configuration ---
# Your bot token will be loaded from a GitHub Secret, not written here.
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# The chat IDs to send the daily questions to.
CHAT_IDS = ["7695772994", "8070930921"]
QUESTIONS_FILE = "post_independence_india.txt"
PROGRESS_FILE = "progress.txt"
QUESTIONS_PER_DAY = 20

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_mcqs(file_path):
    """Parses the text file to extract questions, options, and answers."""
    logger.info(f"Parsing questions from {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Each question block is separated by a blank line.
    # We use a regex lookahead to split by double newlines, keeping them.
    question_blocks = re.split(r'\n\s*\n', content.strip())
    
    parsed_questions = []
    for block in question_blocks:
        if not block.strip():
            continue

        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        
        # Basic validation: must have a question, at least 2 options, and an answer.
        if len(lines) < 4:
            logger.warning(f"Skipping invalid block: {block}")
            continue

        question = lines[0]
        
        # Find the answer line and extract the correct option letter
        answer_line = lines[-1]
        match = re.search(r'Answer:\s*([a-d])', answer_line, re.IGNORECASE)
        if not match:
            logger.warning(f"Could not find answer in block: {block}")
            continue
        correct_option_char = match.group(1).lower()
        
        # The options are the lines between the question and the answer
        options = []
        for line in lines[1:-1]:
            # Strip prefixes like "a)", "b)", etc.
            option_text = re.sub(r'^[a-d]\)\s*', '', line)
            options.append(option_text)

        # Ensure we have exactly 4 options
        if len(options) != 4:
            logger.warning(f"Block does not have 4 options: {block}")
            continue
            
        # Convert 'a'->0, 'b'->1, 'c'->2, 'd'->3
        correct_option_index = ord(correct_option_char) - ord('a')

        parsed_questions.append({
            "question": question,
            "options": options,
            "correct_index": correct_option_index
        })
        
    logger.info(f"Successfully parsed {len(parsed_questions)} questions.")
    return parsed_questions

def main():
    """Main function to run the bot's daily task."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return

    bot = telegram.Bot(token=BOT_TOKEN)
    logger.info("Bot initialized.")

    all_questions = parse_mcqs(QUESTIONS_FILE)
    total_questions = len(all_questions)

    # 1. Read current progress
    start_index = 0
    try:
        with open(PROGRESS_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                start_index = int(content)
        logger.info(f"Read progress: starting from question index {start_index}")
    except FileNotFoundError:
        logger.info("Progress file not found. Starting from the beginning.")
    except (ValueError, IndexError):
        logger.warning("Could not read progress file. Starting from the beginning.")
        start_index = 0

    # 2. Check if we are done
    if start_index >= total_questions:
        logger.info("All questions have been sent.")
        for chat_id in CHAT_IDS:
            try:
                bot.send_message(chat_id=chat_id, text="No more questions, we are done! Congratulations!")
            except Exception as e:
                logger.error(f"Failed to send completion message to {chat_id}: {e}")
        return

    # 3. Determine the batch of questions for today
    end_index = min(start_index + QUESTIONS_PER_DAY, total_questions)
    questions_to_send = all_questions[start_index:end_index]
    logger.info(f"Sending questions from index {start_index} to {end_index - 1}.")

    # 4. Send the polls
    for chat_id in CHAT_IDS:
        logger.info(f"Sending {len(questions_to_send)} polls to chat ID: {chat_id}")
        for i, q_data in enumerate(questions_to_send):
            try:
                bot.send_poll(
                    chat_id=chat_id,
                    question=f"({start_index + i + 1}/{total_questions}) {q_data['question']}",
                    options=q_data['options'],
                    type=telegram.Poll.QUIZ,
                    correct_option_id=q_data['correct_index'],
                    # You can add a timeout to prevent users from being stuck on a question for too long
                    # open_period=600 # 10 minutes
                )
            except Exception as e:
                logger.error(f"Failed to send poll to {chat_id}: {q_data['question']}. Error: {e}")

    # 5. Update the progress file for the next run
    logger.info(f"Updating progress file to index {end_index}")
    with open(PROGRESS_FILE, 'w') as f:
        f.write(str(end_index))
        
    logger.info("Daily task finished successfully.")

if __name__ == "__main__":
    main()
