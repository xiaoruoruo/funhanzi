# GEMINI.md

## Project Overview

This project is a command-line tool designed for learning Chinese characters. It provides a suite of Python scripts to generate tests, record progress, and create study materials. The tool is geared towards students who are learning to read and write Chinese characters, and it uses a database to track performance and tailor study sessions. A notable feature is its integration with the Google Generative AI (Gemini) to enrich study materials with pinyin and vocabulary.

### Key Features:

*   **Test Generation:** Create HTML-based tests for both reading and writing characters from specified lessons.
*   **Progress Tracking:** Record test scores for individual characters in a SQLite database.
*   **Personalized Learning:** Filter characters for tests and study sheets based on past performance (score) and how recently they were studied (date).
*   **AI-Powered Study Sheets:** Generate study sheets that include pinyin and common words for selected characters, powered by the Gemini API.
*   **Word Puzzles:** Create "find the words" puzzles.

### Technologies Used:

*   **Language:** Python 3
*   **Database:** SQLite
*   **AI:** Google Generative AI (Gemini)
*   **Dependency Management:** `uv` (as seen in `uv.lock` and `README.md`)

## Building and Running

This project is run directly from the command line using Python. The following are the primary commands for using the tool, as documented in the `README.md` and inferred from the source code.

### Common Commands

*   **Generate a reading test:**
    ```bash
    python3 exam_read_random.py <num_chars> <lessons> -o <output_filename>
    ```
    *Example:*
    ```bash
    python3 exam_read_random.py 100 1-10 --score_filter=10 --days_filter=7 -o exam_read
    ```

*   **Generate a writing test:**
    ```bash
    uv run exam_write_random_words.py <num_chars> <lessons> -o <output_filename>
    ```
    *Example:*
    ```bash
    uv run exam_write_random_words.py 100 1-10 --score_filter=10 --days_filter=7 -o exam_write
    ```

*   **Record a test result:**
    ```bash
    python3 exam_record.py --type <read|write> --score <0-10> --character <characters>
    ```
    *Example (correct):*
    ```bash
    python3 exam_record.py --type write --score 10 --character 和地树
    ```
    *Example (incorrect):*
    ```bash
    python3 exam_record.py --type write --score 0 --character 着就
    ```

*   **Generate a study sheet:**
    ```bash
    uv run study_chars.py <num_chars> <lessons> -o <output_filename>
    ```
    *Example:*
    ```bash
    uv run study_chars.py --days_filter 5 --score_filter 10 -o study 10 1-10
    ```

*   **Generate a "find the words" puzzle:**
    ```bash
    uv run find_words.py <num_chars> <lessons> -o <output_filename>
    ```
    *Example:*
    ```bash
    uv run find_words.py 30 1-10 -o find_words
    ```

## Development Conventions

*   **Modular Design:** The project is organized into several single-purpose Python scripts (e.g., `exam_read_random.py`, `exam_record.py`, `words.py`). This makes it easy to understand and maintain individual functionalities.
*   **Command-Line Interface:** All scripts are designed to be run from the command line, using the `argparse` module for argument parsing.
*   **Database Migrations:** The `exam_record.py` script includes a simple database migration framework to manage schema changes, which is a good practice for projects with evolving database schemas.
*   **Code Style:** The code is generally well-structured and readable, with clear function and variable names.
*   **HTML Generation:** The project uses helper functions in `exam_formatter.py` to generate HTML files for tests and study sheets, separating the data processing from the presentation.
