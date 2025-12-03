# 📚 Board Booster Bot

A comprehensive Telegram bot for educational content delivery with multi-language support, created by **Team Hackers**.

## 🌟 Features

- **Multi-language Support**: Hindi & English
- **Three Streams**: Non-Medical, Medical, Commerce
- **Comprehensive Subjects**: All major subjects for each stream
- **Admin Panel**: Add chapters, upload content, manage users
- **Anti-Spam System**: Auto-block after 5 random messages
- **Auto-Unblock**: After 24 hours automatically
- **Content Types**: Lectures (MP4), DPPs, Notes (PDF)
- **User Tracking**: Monitor user activity and progress

## 🚀 Quick Deployment on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/XgWx7o?referralCode=team-hackers)

### One-Click Deployment:
1. Click the "Deploy on Railway" button above
2. Add your Telegram Bot Token
3. Add your Telegram ID as admin
4. Deploy!

## 🛠️ Manual Setup

### Prerequisites:
- Node.js 18+ 
- MongoDB
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Installation:

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/board-booster-bot.git
cd board-booster-bot

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start the bot
npm start
