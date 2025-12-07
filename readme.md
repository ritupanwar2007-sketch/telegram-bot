# Board Booster Telegram Bot 📚

A comprehensive board exam preparation bot with admin features for content management.

## Features

### User Features:
- Browse subjects (Physics, Chemistry, Maths, English, Biology)
- Access chapter-wise content
- Three content types: Video Lectures, PDF Notes, DPPs
- Warning system for misuse
- Automatic 24-hour unblock

### Admin Features:
- Add/Delete chapters
- Upload content (videos & PDFs)
- User management (block/unblock)
- View user statistics

## Deployment on Railway

1. **Fork/Clone** this repository

2. **Create new Railway project:**
   - Connect your GitHub repository
   - Railway will auto-detect the Python project

3. **Set Environment Variables:**
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_IDS`: Comma-separated admin user IDs
   - `DATABASE_URL`: Railway provides this automatically

4. **Deploy:**
   - Railway will install dependencies and start the bot

## Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
