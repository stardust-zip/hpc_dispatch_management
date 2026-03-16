# HPC DISPATCH SERVICE

## Project Structure

### Why the main code live inside inside `src/hpc_dispatch_management` but not just `src/`

Python treats directories as Package Names.

In Python, the name of the folder containing your code becomes the name of your package when you import it.

So, if the code live inside `src/`, your package would be named `src` which is too generic.

### Structure (`src/hpc_dispatch_management`)

#### `main.py`

Application entry.

#### `schemas.py`

Valiation schemas for HTTP requests.


#### `core`

Core configurations:
- `settings.py`: Environment variables an appliation settings.
- `security.py`: Authentication, authorization an JWT logic.

#### `db`

Database settings and logic
- `database.py`: Database connection pool and session generation.
- `models.py`: SQLAlchemy table definitions.
- `crud.py`: Logic to interact with the database.
- `seed.py`: Script to inject sample data to database.

#### `routers`

HTTP logics

#### `external_services`

Logic to interact with other microservices in HPC Digital System project.
- `drive_service.py`: Interact with `hpc_drive` to organize and share files.
- `notification_service.py`: Publishes Kafka messages to the notification gateway.
