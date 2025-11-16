# lessons Specification

## Purpose
TBD - created by archiving change add-lesson-management. Update Purpose after archive.
## Requirements
### Requirement: Lesson Data Model
The system SHALL include a `Lesson` model in `studies/models.py` to manage lesson data.

#### Scenario: Lesson Model Definition
- **WHEN** the `studies/models.py` file is examined
- **THEN** a `Lesson` model with `lesson_num` (unique primary key), `is_learned` (defaulting to `False`), and `characters` fields SHALL be present.

### Requirement: Populate Lesson Data
The system SHALL provide a management command to populate the `Lesson` table.

#### Scenario: Populating Lessons from Words
- **WHEN** the management command is executed
- **THEN** `Lesson` instances SHALL be created for each unique lesson number found in the `Word` table, with the `characters` field populated by a comma-separated string of characters for that lesson.

### Requirement: URL Routing for Lesson Management
The system SHALL provide URL paths for listing lessons and toggling their learned status.

#### Scenario: Lesson List URL
- **WHEN** the URL `/lessons/` is accessed
- **THEN** it SHALL map to the `lesson_list` view.

#### Scenario: Toggle Lesson Learned URL
- **WHEN** the URL `/lessons/toggle/<int:lesson_num>/` is accessed
- **THEN** it SHALL map to the `toggle_lesson_learned` view.

### Requirement: Lesson List View
The system SHALL provide a `lesson_list` view to display all lessons.

#### Scenario: Displaying Lessons
- **WHEN** a GET request is made to `/lessons/`
- **THEN** the `lesson_list` view SHALL fetch all `Lesson` objects, ordered by `lesson_num`, and render the `studies/lessons.html` template with the lessons as context.

### Requirement: Toggle Lesson Learned View
The system SHALL provide a `toggle_lesson_learned` view to change a lesson's learned status.

#### Scenario: Toggling Lesson Status
- **WHEN** a POST request is made to `/lessons/toggle/<int:lesson_num>/`
- **THEN** the `toggle_lesson_learned` view SHALL retrieve the specified `Lesson` object, flip its `is_learned` status, save the change, and redirect to the `lesson_list` page.

### Requirement: Lesson List Template
The system SHALL provide a `studies/lessons.html` template to render the lesson list.

#### Scenario: Lesson List Table Structure
- **WHEN** the `studies/lessons.html` template is rendered
- **THEN** it SHALL extend `base.html` and display a table with columns for "Lesson Number", "Characters", "Status", and "Action".

#### Scenario: Lesson Status Display
- **WHEN** a lesson is learned
- **THEN** its status SHALL be displayed as "Learned".
- **WHEN** a lesson is not learned
- **THEN** its status SHALL be displayed as "Not Learned".

#### Scenario: Toggle Button Functionality
- **WHEN** the "Action" button is clicked for a lesson
- **THEN** a POST request SHALL be sent to the `toggle_lesson_learned` URL for that lesson, and the button text SHALL reflect the action to be taken (e.g., "Mark as Unlearned" if learned, "Mark as Learned" if not learned).

### Requirement: Business Logic Update for Character Selection
The core character selection logic in `studies/logic/selection.py` SHALL be updated to filter words based on learned lessons.

#### Scenario: Filtering Words by Learned Lessons
- **WHEN** characters are selected for study or exam generation
- **THEN** the system SHALL query the `Lesson` model to identify all `lesson_num` where `is_learned` is `True`.
- **THEN** only `Word` objects whose `lesson` field is within this list of learned lesson numbers SHALL be considered for selection.

### Requirement: Admin Interface for Lesson Model
The `Lesson` model SHALL be registered with the Django admin interface.

#### Scenario: Lesson Model in Admin
- **WHEN** the Django admin interface is accessed
- **THEN** the `Lesson` model SHALL be visible and editable, allowing for manual overrides of lesson data.

