# TechTive

🥇  **Best Overall/1st Place Team** @ **Cornell AppDev Hackathon (Fall 2024)** out of 30+ teams and 140+ participants.

🚀 A fully functional [prototype](http://34.21.62.193/api/advice/latest/) of TechTive backend has been successfully deployed and is accessible!

🔨 **Backend Developers**: George Dong | Abrar Amin

📱 [**Frontend Developers and Repository**](https://github.com/JiwonJeong414/TechTive-iOS/): Jiwon Jeong | Keya Aggarwal

## Table of Contents
- [Application Description](#application-description)
- [Tech Stack and Tools](#tech-stack-and-tools)
- [System Design Overview](#system-design-overview)
    - [Modular Design Pattern](#modular-design-pattern)
    - [Asynchronous Parallel Processes](#asynchronous-parallel-processes)
    - [Scalable Workers](#scalable-workers)
- [API Endpoints Overview](#api-endpoints-overview)
- [Appendix](#appendix)

## Application Description
TechTive is a journaling platform designed to help users gain data-driven insights into their thoughts and emotions. The app uses sentiment analysis to evaluate and score journal entries, providing users a better understanding of their emotional state across various categories. At the end of each week, TechTive uses the user's weekly journaling patterns to deliver personalized advice in the form of a riddle to help them prepare for the upcoming week.

## Tech Stack and Tools
- **Nginx** – Reverse proxy for routing incoming requests to the Flask service.  
- **Firebase** – Provides user authentication via Bearer tokens.  
- **Flask (with Blueprints)** – Main server-side framework for routing and business logic.  
- **SQLAlchemy & PostgreSQL** – ORM and a relational database for storing users, posts, and weekly advice.  
- **RabbitMQ** – Message broker for queuing background tasks.  
- **Celery** – Task queue library used to create background jobs for parallel processing.  
- **Celery Beat** – Job scheduler that periodically enqueues batch of tasks (e.g., generating weekly advice).  

## System Design Overview
<img src="https://drive.google.com/uc?export=view&id=1A1pdA6KfASGWZtRWAHGzh8L7jysfTyhQ" alt="System Design Diagram" width="1000" width="1000">

### Modular Design Pattern
- The application uses Flask Application Factory and Extensions to encapsulate the creation and configuration of different services, allowing for the separation of concerns.
- Long-running tasks—like generating weekly advice or computing emotional scores—are handed off to Celery workers, allowing the main Flask service to respond quickly.  

### Asynchronous Parallel Processes
- Tasks are placed on a RabbitMQ messaging queue and processed by multiple Celery workers running concurrently.
- Celery Beat triggers a batch advice-generation job every Sunday at 12:00 UTC. Each user’s weekly advice generation is executed in its Celery task to avoid bottlenecks.
- Automatic retries and error handling ensure external API failures (e.g., OpenAI, Hugging Face) do not interrupt the main application flow.

### Scalable Workers
- Each worker can be assigned at most one tasks by default (configurable via the --concurrency flag).
- Additional worker containers can be spun up easily through Docker Compose.
- Future releases will focus on migrating containers to separate computing instances and using orchestrators to make this architecture highly scalable.

## API Endpoints Overview

All endpoints require a valid Firebase Bearer token in the `Authorization` header. Below is a high-level overview of the main endpoints. 

1. **Posts**  
   - **`POST /api/post/`**: Create a new journal post.  
   - **`PUT /api/post/<post_id>/`**: Update an existing post.  
   - **`GET /api/posts/`**: Retrieve all posts for the authenticated user.  
   - **`GET /api/post/<post_id>/`**: Retrieve a single post by ID.  

2. **Weekly Advice**  
   - **`GET /api/advice/latest/`**: Fetch the latest riddle-like advice for the current week.  

3. **Profile Picture**  
   - **`POST /api/pfp/`**: Upload or overwrite the user’s profile picture in S3.  
   - **`GET /api/pfp/`**: Retrieve the current user’s profile picture URL.  
   - **`DELETE /api/pfp/`**: Delete the user’s profile picture from S3.  


## Appendix

### I. Authentication
All API requests must have a valid **Firebase Bearer token** to be passed in the `Authorization` header as `Bearer <TOKEN>`. The API will return an appropriate HTTP error if the token is invalid or missing. 

```
Authorization: Bearer <Firebase_ID_Token>
```

### II. Journal Entry/Post

#### a. Retrieve a Specific Entry
- **GET** `/api/posts/{id}/`
- **Response**
  ```
  <HTTP STATUS CODE 200>
  
  <STORED ENTRY WITH FORMAT AND PREDICTED EMOTION DATA, EXAMPLE BELOW>
  {
    "message": "Successfully retrieved post ID {id}.",
    "post": {
      "id": <ID>,
      "user_id": <STORED USER ID FOR ENTRY WITH ID {id}>,
      "content": "String text from journal entry.",
      "formatting": [
        {"range": {"location": 4, "length": 5}, "type": "bold"},
        <STORED FORMAT DATA OF CHAR WIDTH AND FORMAT TYPE FOR ENTRY WITH ID {id}>
      ],
      "joy_value": 0.98,
      "neutral_value": 0.01,
      "sadness_value": 0.004,
      ... other emotion categories and values ...
      "created_at": "2025-01-06T13:37:29.534964+00:00
    }
  }
  ```

#### b. Create a New Entry
- **POST** `/api/posts/`
- **Request Body**
  ```
  {
    "content": "String text from journal entry.",
    "formatting": <USER INPUT (OPTIONAL JSON)>
  }
  ```
- **Response**
  ```
  <HTTP STATUS CODE 201>
  
  <CREATED POST WITHOUT EMOTION SCORES, EXAMPLE BELOW>
  {
    "message": "Successfully created new post. Check back in a minute for emotional score.",
    "post": {
      "id": <ID>,
      "user_id": <STORED USER ID FOR CREATED ENTRY>,
      "content": "String text from journal entry.",
      "formatting": <USER INPUT, OTHERWISE EMPTY JSON>,
      "created_at": <STORED UTC DATETIME FOR CREATED ENTRY>
    }
  }
  ```

#### c. Update an Existing Entry
- **PUT** `/api/posts/{id}/`
- **Request Body**
  ```
  {
    "content": "Updated text for journal entry",
    "formatting": <USER INPUT (OPTIONAL JSON)>
  }
  ```
- **Response**
  ```
  <HTTP STATUS CODE 200>

  <UPDATED POST WITHOUT NEW EMOTION SCORES, EXAMPLE BELOW>
  {
    "message": "Successfully updated post {id}. Check back in a minute for emotional score.",
    "post": {
      ...
      "content": "Updated text for journal entry.",
      "formatting": <USER INPUT, OTHERWISE EMPTY JSON>,
      "created_at": <STORED NEW UTC DATETIME FOR UPDATED ENTRY>
    }
  }
  ```

#### d. Retrieve All Entries
- **GET** `/api/posts/`
- **Response**
  ```
  <HTTP STATUS CODE 200>
  {
    "message": "Successfully retrieved <NUMBER OF ENTRIES> posts by user <ID>.",
    "posts": [
      <JOURNAL ENTRY>,
      <JOURNAL ENTRY>
    ]
  }
  ```

### III. Weekly Advice
#### a. Retrieve Latest Weekly Advice
- **GET** `/api/advices/latest/`
- **Response**
  ```
  <HTTP STATUS CODE 200>

  <STORED WEEKLY ADVICE, EXAMPLE BELOW FROM SUNDAY, JAN 12TH, 2025>
  {
    "message": "Successfully retrieved latest advice for week of 2025-01-06.",
    "user_id": <STORED USER ID FOR WEEKLY ADVICE>,
    "content": {
      "riddle": "I can lift your spirits high, yet too much can make you sigh. I am the thrill of success, 
                but without rest, I can cause distress. What am I?",
      "answer": "Balance",
      "advice": "As you move into the upcoming week, remember to find balance in your efforts and rest. 
                Celebrate your achievements, but also take time to recharge."
    },
    "created_at": "2025-01-06T13:37:29.534964+00:00",
    "week_of": "2025-01-06"
  }
  ```

### IV. Profile Picture
#### a. Retrieve Latest Profile Picture
- **GET** `/api/pfp/`
- **Response**
  ```
  <HTTP STATUS CODE 200>

  {
    "message": "Successfully retrieved profile picture.",
    "link": <S3 BUCKET LINK>
  }
  ```

#### b. Upload a Profile Picture
- **POST** `/api/pfp/`
- **Request (Form-Data)**
  - **Key:** `ImageFile`  
  - **Value:** (Binary image data, allowed types: `.png`, `.jpg`, `.jpeg`)
- **Response**
  ```
  <HTTP STATUS CODE 201>

  {
    "message": "Successfully uploaded profile picture.",
    "link": <S3 BUCKET LINK>
  }
  ```

#### c. Delete the Profile Picture
- **DELETE** `/api/pfp/`
- **Response**
  ```
  <HTTP STATUS CODE 200>

  {
    "message": "Successfully deleted profile picture.",
    "link": <S3 BUCKET LINK>
  }
  ```