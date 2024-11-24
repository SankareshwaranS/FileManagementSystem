# File Management System (FMS)

## Overview
The **File Management System (FMS)** is a backend solution built with Django that provides functionality for managing files and folders in a hierarchical structure. It includes features such as CRUD operations, file uploads, moving items, and listing folder contents. The application ensures robust data integrity and synchronization with the underlying file system.

---

## Features
- **File and Folder Management**: Create, update, and delete files and folders.
- **File Uploads**: Upload files to specific folders with validation.
- **Move Functionality**: Move files or folders between directories.
- **Folder Contents Listing**: Paginated and searchable listing of folder contents.
- **Hierarchical Structure**: Parent-child relationships for files and folders.
- **Database Synchronization**: Ensures the database matches the file system structure.

---

## Technology Stack
- **Framework**: Django and Django REST Framework  
  Chosen for robust development capabilities, security features, and seamless API integration.
- **Database**: PostgreSQL  
  Preferred for its performance, reliability, and support for relational data structures.
- **File Storage**: Local file system  
  Files and folders are dynamically managed to mirror the database hierarchy.

---

## Architecture

### Layers
- **Models**:  
  The `Item` model represents both files and folders with attributes such as:
  - `name` (string)
  - `type` (`file` or `folder`)
  - `parent` (ForeignKey for parent-child relationships)
  - `file_path` (for files)

  - A folder can contain sub-items (files or folders).  
  - A file must belong to a folder.

- **Views**:  
  `ItemViewSet` manages CRUD operations and includes custom actions for:
  - Listing folder contents
  - Uploading files
  - Moving items between directories

- **Database**:  
  PostgreSQL stores hierarchical relationships between files and folders using foreign keys to manage parent-child connections.

- **File System**:  
  Files and folders are stored locally on disk, and their structure mirrors the database hierarchy.

---

## Validation
- Files must belong to valid folders.
- Duplicate names are not allowed in the same folder.

---

## Setup Instructions

### Prerequisites
- **Python** 3.12
- **PostgreSQL** 12+
- **pip** (Python package manager)

### Installation Steps

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/yourusername/fms.git
    cd fms
    ```

2. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Database Configuration**:  
   Update the `DATABASES` setting in `settings.py` with your PostgreSQL credentials:
    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'fms_db',
            'USER': 'your_postgres_user',
            'PASSWORD': 'your_postgres_password',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
    ```

4. **Run Migrations**:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5. **Start the Server**:
    ```bash
    python manage.py runserver
    ```

6. **Access the Application**:  
   Visit [http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/) to interact with the API.

---

## API Endpoints

### Folder and File Management

1. **List Folder Contents**  
   **GET** `/api/items/list-contents/`  
   **Parameters**:
   - `id`: Folder ID (optional, lists all items if not provided).
   - `search`: Search term (optional).
   - `ordering`: Ordering field (optional).

2. **Create Folder/File**  
   **POST** `/api/items/`  
   **Payload**:
    ```json
    {
        "name": "example",
        "type": "folder",
        "parent": null
    }
    ```

3. **Move Item**  
   **POST** `/api/items/move-item/`  
   **Payload**:
    ```json
    {
        "item_id": 1,
        "new_parent_id": 2
    }
    ```

4. **Delete Item**  
   **DELETE** `/api/items/{id}/`

---

## Project Features

### Validation
- Files can only exist within folders.
- Folders cannot contain items with duplicate names.

### Pagination and Search
- Pagination allows efficient listing of large directories.
- Search enables finding files or folders by name.

### Transactions
- Operations like file upload, update, and move are wrapped in database transactions to ensure consistency.

---

## Future Enhancements
- **User Authentication**: Add user-based access controls to secure the system.
- **Cloud Storage**: Integrate with solutions like AWS S3 or Google Cloud Storage.
- **Version Control**: Enable versioning for files to track changes.
- **Role-Based Access Control (RBAC)**: Facilitate multi-user collaboration with granular permissions.
