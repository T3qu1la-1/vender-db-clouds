# Flask TXT Processor Application

## Overview
This is a Flask web application designed for processing TXT files containing credential data in the format `url:user:pass`. The application provides an intuitive interface for uploading, processing, filtering, and downloading credential files.

## Project Structure
- `app.py` - Main Flask application with all routes and processing logic
- `main.py` - Entry point for running the application
- `pyproject.toml` - Project dependencies and configuration
- `app_backup.py` / `app_old.py` - Backup versions of the application

## Features
- Upload and process multiple TXT/ZIP/RAR files
- In-memory processing without file storage
- Brazilian URL filtering capabilities
- SQLite database conversion
- Modern dark-themed Bootstrap interface
- Real-time statistics dashboard

## Dependencies
- Flask 3.1.2+ - Web framework
- Gunicorn 23.0.0+ - WSGI server
- Email-validator 2.2.0+ - Input validation
- Flask-SQLAlchemy 3.1.1+ - Database ORM
- Psycopg2-binary 2.9.10+ - PostgreSQL adapter

## Environment Setup
- Configured for Replit environment with proxy middleware
- Uses environment variables for session secrets
- Database URL from environment (PostgreSQL available but app uses SQLite)
- Runs on port 5000 with webview output

## Recent Changes (September 2, 2025)
- Restored main app.py from backup version
- Configured Flask app with ProxyFix middleware for Replit
- Set up proper workflow configuration for web preview
- Installed all required dependencies via UV package manager
- Configured deployment settings for autoscale deployment

## User Preferences
- Application is in Portuguese (PT-BR)
- Dark theme interface with gradient styling
- File processing focused on Brazilian credential filtering

## Architecture
- Single Flask application with embedded HTML templates
- In-memory session data storage
- Temporary SQLite database creation for conversion features
- No persistent file storage - all processing is temporary