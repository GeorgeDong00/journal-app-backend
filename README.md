# TechTive Backend

TechTive is an AI-assisted journaling app built during the Cornell AppDev Hackathon in Fall 2024, where the project placed 1st overall. This repository contains the Flask backend used by the iOS app for authentication, journal storage, AI-powered emotion scoring, weekly advice generation, and profile picture storage.

- Backend developers: George Dong, Abrar Amin
- Frontend developers: Jiwon Jeong, Keya Aggarwal

## Contents

- [Overview](#overview)
- [Technical Highlights](#technical-highlights)
- [AI Features](#ai-features)
- [System Design](#system-design)
- [Deployment](#deployment)
- [Tech Stack](#tech-stack)
- [API Reference](#api-reference)
- [Running Locally](#running-locally)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)

## Overview

- Frontend repository: [TechTive iOS](https://github.com/JiwonJeong414/TechTive-iOS/)
- Demo backend endpoint used during the hackathon: [latest weekly advice](http://34.21.62.193/api/advices/latest/)

TechTive helps users reflect on their journal entries by combining normal journaling features with AI-generated feedback. The backend provides the API and background processing needed to support that experience from the mobile app.

## Technical Highlights

- Built a Flask API for authenticated journal entry CRUD, weekly advice lookup, and profile picture management.
- Integrated Firebase token verification so each request is tied to the correct user.
- Used PostgreSQL with SQLAlchemy models for users, journal entries, emotion scores, and weekly advice.
- Moved slower AI calls into Celery workers with RabbitMQ, keeping user-facing API requests responsive.
- Added scheduled weekly advice generation with Celery Beat.
- Integrated Hugging Face for emotion classification and OpenAI for structured advice generation.
- Stored profile pictures in AWS S3 and returned public profile picture URLs through the API.
- Deployed the Docker Compose backend stack on a Google Cloud VM for the hackathon demo.

## AI Features

The project uses AI in two parts of the product.

**Emotion scoring:** When a user creates or updates a journal entry, Flask saves the entry first and queues a Celery task. The worker sends the journal text to a Hugging Face emotion classification model and stores scores for anger, disgust, fear, joy, neutral, sadness, and surprise.

**Weekly advice:** Celery Beat runs a scheduled job every Sunday at 12:00 UTC. The job queues one task per user, gathers that user's entries from the current week, and sends them to the OpenAI API. The response is stored as structured JSON with a riddle, answer, and short advice message.

Beyond the model calls, the backend handles prompt formatting, JSON parsing, supported-label checks for emotion scores, retries for third-party API failures, and guards against duplicate weekly advice.

## System Design

Client requests go through Nginx to the Flask API. Flask handles authentication, request validation, and database writes. RabbitMQ queues longer AI jobs, and Celery workers process those jobs outside the main request cycle. PostgreSQL stores application data, and S3 stores profile pictures.

<img src="https://drive.google.com/uc?export=view&id=1A1pdA6KfASGWZtRWAHGzh8L7jysfTyhQ" alt="TechTive backend architecture diagram" width="1000">

### Request Flow

1. The iOS app sends an authenticated API request.
2. Flask verifies the Firebase token and handles the request.
3. Journal data is saved in PostgreSQL.
4. AI work is queued in RabbitMQ.
5. Celery workers call the external AI service and update the database when results are ready.

## Deployment

For the hackathon demo, the backend was deployed on a Google Cloud VM instance. The VM ran the backend stack with Docker Compose, exposed Nginx publicly, and forwarded traffic to the Flask app running behind Gunicorn.

The VM deployment used the same core services as the local environment:

- Flask API served with Gunicorn
- Nginx reverse proxy
- PostgreSQL database
- RabbitMQ message broker
- Celery worker for AI background jobs
- Celery Beat scheduler for weekly advice generation

This was a single-VM prototype deployment, not a large production system. It gave the team a public backend endpoint for the iOS app while keeping the service setup close to the local Docker environment.

## Tech Stack

| Area | Tools |
| --- | --- |
| API | Flask, Gunicorn, Nginx |
| Authentication | Firebase Admin SDK |
| Database | PostgreSQL, SQLAlchemy, Flask-Migrate |
| Validation and Serialization | Marshmallow |
| Background Jobs | Celery, Celery Beat, RabbitMQ |
| AI Services | OpenAI API, Hugging Face Inference API |
| File Storage | AWS S3 |
| Containerization | Docker Compose |
| Cloud Deployment | Google Cloud VM |

## API Reference

All endpoints require this header:

```text
Authorization: Bearer <Firebase_ID_Token>
```

### Journal Entries

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/posts/` | Create a journal entry. |
| `GET` | `/api/posts/` | Get all entries for the authenticated user. |
| `GET` | `/api/posts/<post_id>/` | Get one entry owned by the authenticated user. |
| `PUT` | `/api/posts/<post_id>/` | Update one entry owned by the authenticated user. |
| `DELETE` | `/api/posts/<post_id>/` | Delete one entry owned by the authenticated user. |

Create or update request body:

```json
{
  "content": "Journal entry text",
  "formatting": []
}
```

`content` is required. `formatting` is optional and defaults to an empty list. Create and update responses return the saved entry before new emotion scores are available.

### Weekly Advice

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/advices/latest/` | Get the authenticated user's advice for the current week. |

Example advice content:

```json
{
  "riddle": "I rise when you pause, and fade when you rush. What am I?",
  "answer": "Calm",
  "advice": "Give yourself room to slow down next week before taking on more."
}
```

### Profile Picture

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/pfp/` | Get the authenticated user's profile picture URL. |
| `POST` | `/api/pfp/` | Upload or replace the authenticated user's profile picture. |
| `DELETE` | `/api/pfp/` | Delete the authenticated user's profile picture. |

Profile picture uploads use form data:

```text
ImageFile=<png, jpg, or jpeg file>
```

## Running Locally

The repository includes a Docker Compose setup for the backend services.

1. Create a `.env` file with the required values listed below.
2. Start the stack:

   ```bash
   docker compose up --build
   ```

3. Send API requests through Nginx:

   ```text
   http://localhost/
   ```

RabbitMQ's management UI is available at `http://localhost:15672` when the stack is running.

Database migrations are supported through Flask-Migrate, but this repository does not include a committed migrations folder.

## Environment Variables

The app reads configuration from a `.env` file when running through Docker Compose.

| Category | Variable | Purpose |
| --- | --- | --- |
| Flask | `SECRET_KEY` | Flask application secret key. |
| Firebase | `FIREBASE_CREDENTIAL` | Firebase service account JSON used to verify ID tokens. |
| PostgreSQL | `DATABASE_URL` | SQLAlchemy database connection string. |
| PostgreSQL | `POSTGRES_DB` | Database name used by the Postgres container. |
| PostgreSQL | `POSTGRES_USER` | Database user used by the Postgres container. |
| PostgreSQL | `POSTGRES_PASSWORD` | Database password used by the Postgres container. |
| RabbitMQ | `RABBITMQ_USER` | RabbitMQ user for the broker container. |
| RabbitMQ | `RABBITMQ_PASSWORD` | RabbitMQ password for the broker container. |
| Celery | `RABBITMQ_BROKER_URL` | Broker URL used by Celery to enqueue tasks. |
| Celery | `RABBITMQ_RESULT_BACKEND` | Celery result backend URL. |
| OpenAI | `OPENAI_API_KEY` | API key for weekly advice generation. |
| Hugging Face | `HUGGING_FACE_API_TOKEN` | API token for emotion scoring. |
| Hugging Face | `EMOTION_SCORE_API_URL` | Hugging Face model endpoint for emotion classification. |
| AWS S3 | `AWS_REGION` | AWS region for the S3 bucket. |
| AWS S3 | `AWS_ACCESS_KEY_ID` | AWS access key for profile picture uploads. |
| AWS S3 | `AWS_SECRET_ACCESS_KEY` | AWS secret key for profile picture uploads. |
| AWS S3 | `S3_PROFILE_PIC_BUCKET` | S3 bucket name for profile pictures. |
| AWS S3 | `S3_PROFILE_PIC_BUCKET_URL` | Public base URL for uploaded profile pictures. |

`FIREBASE_CREDENTIAL` should be stored as a single-line JSON string in `.env`.

## Project Structure

```text
app/
  main/                  Flask routes and JSON error handlers
  models/                SQLAlchemy models and Marshmallow schemas
  celery_worker/         Celery task definitions and task logic
  utils/                 Authentication, time, advice, and exception helpers
  config.py              Environment-based configuration
  extensions.py          Database, migration, schema, and S3 setup
celery_factory.py        Celery application factory
docker-compose.yml       Local service orchestration
Dockerfile.web           Flask/Gunicorn image
Dockerfile.celery        Celery worker and scheduler image
nginx/nginx.conf         Reverse proxy configuration
run.py                   Flask and Celery entry point
```
