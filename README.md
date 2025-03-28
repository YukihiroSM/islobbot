# ISLOB Bot

A Telegram fitness tracking and coaching bot that helps users monitor their training, sleep, stress levels, and overall well-being.

## Overview

ISLOB Bot is a comprehensive fitness tracking solution that interacts with users through Telegram. The bot collects data about users' training sessions, sleep patterns, stress levels, and general well-being through regular check-ins and quizzes. It provides personalized statistics, visualizations, and insights to help users optimize their fitness journey.

## Features

- **Morning Quizzes**: Daily check-ins to track sleep quality, weight, and overall feelings
- **Training Tracking**: Log training sessions with details on duration, intensity, and discomfort
- **Post-Training Feedback**: Collect data on stress and soreness after workouts
- **Automated Notifications**: Customizable reminders for morning check-ins and training sessions
- **Statistics Visualization**: Visual representation of sleep patterns, stress levels, and training intensity
- **AI-Powered Insights**: Utilizes OpenAI's GPT models to analyze fitness data and provide personalized recommendations

## Tech Stack

- **Backend**: Python with SQLAlchemy ORM
- **Database**: PostgreSQL
- **Bot Framework**: python-telegram-bot
- **Data Visualization**: Matplotlib, Seaborn, Pandas
- **AI Integration**: OpenAI API (GPT models)
- **Scheduling**: APScheduler
- **Database Migrations**: Alembic

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Telegram Bot Token (from BotFather)
- OpenAI API Key

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/YukihiroSM/islobbot.git
   cd islobbot
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with the following variables:
   ```
   TOKEN=your_telegram_bot_token
   DATABASE_URL=postgresql://username:password@localhost/islobbot
   ADMIN_CHAT_IDS=["your_telegram_chat_id"]
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_ASSISTANT_ID=your_openai_assistant_id
   ```

4. Initialize the database:
   ```
   python init_db.py
   ```

5. Run the bot:
   ```
   python main.py
   ```

## Database Schema

The database consists of several main tables:

- **Users**: Stores user information and preferences
- **NotificationPreference**: Manages notification settings for each user
- **Training**: Records training sessions with details
- **MorningQuiz**: Stores daily check-in data

## Conversations Flow

The bot implements several conversation flows:

### 1. Introduction Conversation
- **Purpose**: Onboards new users and collects initial information
- **Flow**:
  - Starts with the `/start` command
  - Collects the user's full name
  - Asks for preferred morning notification time
  - Sets up morning notification preferences
  - Directs user to the main menu

### 2. Morning Quiz Conversation
- **Purpose**: Daily check-in for sleep, weight, and well-being
- **Flow**:
  - Triggered by a scheduled morning notification
  - Asks how the user feels (1-10 scale)
  - Collects sleep duration (hours:minutes)
  - Records user's current weight
  - Asks if the user plans to train today
  - If yes, collects expected training time
  - Creates training notifications if needed
  - Saves all data to the database

### 3. Training Start Conversation
- **Purpose**: Initiates a training session
- **Flow**:
  - Triggered when user selects "Start Training"
  - Asks for pre-training feeling (1-10 scale)
  - Records training start time
  - Sends training PDF document (personalized or default)
  - Updates notification statuses
  - Provides "End Training" button

### 4. Training Finish Conversation
- **Purpose**: Completes a training session and collects feedback
- **Flow**:
  - Triggered when user selects "End Training"
  - Asks for training hardness rating (1-10 scale)
  - Asks if user experienced any pain/discomfort
  - If yes, notifies admin users about the issue
  - Records training duration and end time
  - Updates notification statuses
  - Displays motivational message
  - Returns to main menu

### 5. After Training Conversation
- **Purpose**: Follow-up on stress and soreness levels after training
- **Flow**:
  - Triggered by scheduled notification the day after training
  - Asks for stress level (1-10 scale)
  - Asks if user is experiencing muscle soreness
  - Records responses in the database
  - Returns to main menu

### 6. PDF Assignment Conversation
- **Purpose**: Allows admins to assign training PDF documents to users
- **Flow**:
  - Triggered when admin selects "Training PDF"
  - Displays list of users
  - Admin selects a user
  - Admin uploads PDF document
  - System assigns PDF to selected user
  - Notifies user about new training document
  - Returns to main menu

## Statistics Visualization

The statistics system generates visualizations with the following characteristics:
- Sleep data is displayed as a bar chart
- Stress, hardness, and feelings are displayed as line plots
- All plots use day.month (DD.MM) format for x-axis labels

### Data Collection and Analysis

The statistics system collects and analyzes several types of user data:
- **Sleep Duration**: Tracked daily through morning quizzes
- **Feelings/Well-being**: Self-reported ratings on a 1-10 scale
- **Training Hardness**: User-reported difficulty of each workout
- **Stress Levels**: Post-training stress measurements
- **Muscle Soreness**: Tracked after training sessions (marked with X on hardness plots)

### Visualization Components

The system generates a comprehensive visualization with four main components arranged in a 2x2 grid:
1. **Sleep Chart (Bottom Left)**: Bar chart displaying sleep duration in hours for each day
2. **Stress Chart (Top Left)**: Line plot showing stress levels over time
3. **Training Hardness Chart (Top Right)**: Line plot with special X markers for sessions that caused muscle soreness
4. **Feelings Chart (Bottom Right)**: Line plot tracking overall well-being

All charts use a consistent date format (DD.MM) on the x-axis for easy readability, and the system employs a clean, whitegrid theme with pastel colors for improved visual aesthetics.

### Time Periods

Statistics can be generated for different time periods:
- **Weekly**: Data from the past 7 days
- **Monthly**: Data from the past 28 days

### AI-Powered Insights

The statistics system leverages OpenAI's Assistant API to analyze the collected data and provide personalized insights about:
- Training patterns and their effectiveness
- Sleep quality and its impact on performance
- Stress levels and recovery patterns
- Overall fitness progress and trends

These AI-generated insights are presented alongside the statistical visualizations to provide users with a comprehensive understanding of their fitness journey.

### Technical Implementation

The visualization system is built using:
- **Pandas**: For data manipulation and analysis
- **Matplotlib**: For creating the visualization framework and grid layout
- **Seaborn**: For enhanced visual aesthetics with a pastel color palette
- **OpenAI API**: For AI-powered analysis of fitness data

The system follows a consistent visual style with a clean, whitegrid theme and pastel colors for improved readability and user experience. The implementation specifically uses bar charts for sleep data visualization while maintaining line plots for other metrics, as per the project's design preferences.

## AI Integration

The system leverages an existing OpenAI Assistant for analyzing fitness metrics. This integration requires:

1. **Assistant Setup**: An OpenAI Assistant must be configured specifically for fitness data analysis with the following capabilities:
   - Understanding training patterns and their impact on user well-being
   - Analyzing sleep quality and its correlation with training performance
   - Monitoring stress levels and suggesting recovery strategies
   - Tracking overall progress and providing motivational feedback

2. **Environment Configuration**: The Assistant ID must be configured in the `.env` file:
   ```
   OPENAI_ASSISTANT_ID=your_openai_assistant_id
   ```

3. **Data Processing Overview**: The system collects user data from morning quizzes and training sessions, which is then used to generate personalized insights and recommendations.

### Benefits of AI Integration

- **Personalized Insights**: The AI analyzes individual patterns that might not be obvious from charts alone
- **Holistic Analysis**: Considers the relationship between different metrics (sleep, stress, training intensity)
- **Actionable Recommendations**: Provides specific suggestions to improve training outcomes
- **Motivational Support**: Offers encouragement based on progress and achievements

To use this feature, you must configure an OpenAI Assistant and set the `OPENAI_ASSISTANT_ID` in your `.env` file.

## Deployment

The project includes Docker configuration for easy deployment:

1. Build and run with Docker Compose:
   ```
   docker-compose up -d
   ```

This will start the bot and PostgreSQL database in containers.

## Development

### Database Migrations

The project uses Alembic for database migrations:

```
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Code Style

The project follows PEP 8 style guidelines. You can format your code using Black:

```
black .
```
