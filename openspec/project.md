# FunHanzi Project Specification

This document outlines the core mission, technical stack, and development conventions for the FunHanzi project.

## 1. Project Overview

FunHanzi is a web application designed to help users learn Chinese characters effectively and enjoyably. It leverages a Spaced Repetition System (SRS) to optimize learning and provides tools for generating exams and study materials. The core mission is to create an engaging and personalized learning experience.

The project is currently undergoing a migration to a more robust and scalable architecture. The legacy Flask/SQLite stack is being replaced by a Django/PostgreSQL stack. All new development should adhere to the target architecture outlined in this document.

## 2. Tech Stack (Target Architecture)

The FunHanzi application is built on the following technologies:

*   **Backend Framework:** Django
*   **Database:** PostgreSQL
*   **Spaced Repetition:** `py-fsrs`
*   **AI Integration:** Gemini API for dynamic content generation.
*   **Frontend:**
    *   HTML templates managed by the Django template engine.
    *   Bootstrap CSS for styling.
*   **Python Environment:** Managed using `uv`.

## 3. Project Conventions

Adherence to these conventions is crucial for maintaining code quality and consistency.

*   **Dependency Management:** All Python dependencies are managed in `pyproject.toml`. Use `uv sync` to install or update dependencies.
*   **Running Commands:** All Python and Django management commands must be executed within the virtual environment using `uv run`.
    *   Example: `uv run python funhanzi/manage.py runserver`
*   **Code Style:** Follow PEP 8 for Python code. Use a linter/formatter like `ruff` to ensure consistency.
*   **Database Migrations:** All database schema changes must be managed through Django's migration system (`makemigrations`, `migrate`). Direct database alterations are forbidden.
*   **Business Logic:**
    *   Core business logic (FSRS, card selection, content generation) is located in the `studies/logic/` directory.
    *   Logic should be decoupled from the views and operate on Django model instances.
    *   Content generation functions should return JSON-serializable Python dictionaries, not HTML.
*   **Views and Templates:**
    *   Views are responsible for handling HTTP requests/responses and calling business logic.
    *   Templates are responsible for rendering the data provided by the views. Avoid embedding complex logic in templates.
*   **Static Files:** All static assets (CSS, JS, images) are managed by Django's static file system and located in `studies/static/studies/`.
*   **Testing:** Automated tests are a priority. Refer to the project's testing strategy document for details on writing and running tests.

## 4. Core Architectural Principles

*   **Database-Driven Content:** Study and exam content is generated dynamically and stored as JSON in the database. This replaces the old method of generating static HTML files, allowing for more flexibility and dynamic rendering.
*   **Separation of Concerns:** The application follows Django's Model-View-Template (MVT) pattern to ensure a clear separation between data (models), presentation (templates), and control logic (views).
*   **Scalability:** The move to PostgreSQL provides a robust and scalable database backend capable of handling concurrent users and larger datasets.
*   **Maintainability:** By leveraging Django's features (ORM, Admin, security) and adhering to clear conventions, the codebase is designed to be maintainable and extensible over the long term.
