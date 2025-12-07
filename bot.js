const express = require('express');
const { Telegraf, Markup, session } = require('telegraf');
const mongoose = require('mongoose');
const cron = require('node-cron');
require('dotenv').config();

// Initialize Express for Railway health checks
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware for parsing
app.use(express.json());

// Health check endpoint
app.get('/', (req, res) => {
    res.status(200).json({
        status: 'ok',
        service: 'Board Booster Bot',
        message: 'Bot is running successfully',
        timestamp: new Date().toISOString(),
        createdBy: 'Team Hackers'
    });
});

app.get('/health', (req, res) => {
    res.status(200).json({ 
        status: 'healthy',
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// Database Models
const userSchema = new mongoose.Schema({
    telegramId: { type: String, required: true, unique: true },
    username: String,
    firstName: String,
    lastName: String,
    language: { type: String, default: 'english' },
    stream: String,
    subject: String,
    currentChapter: String,
    messageCount: { type: Number, default: 0 },
    isBlocked: { type: Boolean, default: false },
    blockedUntil: Date,
    isAdmin: { type: Boolean, default: false },
    lastMessageTime: Date,
    createdAt: { type: Date, default: Date.now }
});

const chapterSchema = new mongoose.Schema({
    stream: { type: String, required: true },
    subject: { type: String, required: true },
    chapterName: { type: String, required: true },
    chapterNumber: Number,
    addedBy: String,
    addedAt: { type: Date, default: Date.now }
});

const contentSchema = new mongoose.Schema({
    chapterId: { type: mongoose.Schema.Types.ObjectId, ref: 'Chapter' },
    contentType: { type: String, enum: ['lecture', 'dpp', 'notes'] },
    fileId: { type: String, required: true },
    fileName: String,
    caption: String,
    addedBy: String,
    addedAt: { type: Date, default: Date.now }
});

const User = mongoose.model('User', userSchema);
const Chapter = mongoose.model('Chapter', chapterSchema);
const Content = mongoose.model('Content', contentSchema);

// Bot Configuration
const BOT_TOKEN = process.env.BOT_TOKEN;
const ADMIN_IDS = process.env.ADMIN_IDS ? process.env.ADMIN_IDS.split(',') : [];
const RAILWAY_ENVIRONMENT = process.env.RAILWAY_ENVIRONMENT === 'true';

if (!BOT_TOKEN) {
    console.error('❌ BOT_TOKEN is required!');
    process.exit(1);
}

// Initialize bot with error handling
let bot;
try {
    bot = new Telegraf(BOT_TOKEN);
    console.log('✅ Bot instance created successfully');
} catch (error) {
    console.error('❌ Failed to create bot instance:', error.message);
    process.exit(1);
}

// MongoDB Connection with retry logic
const connectDB = async () => {
    try {
        await mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/boardbooster', {
            useNewUrlParser: true,
            useUnifiedTopology: true,
            serverSelectionTimeoutMS: 5000,
            connectTimeoutMS: 10000
        });
        console.log('✅ Connected to MongoDB');
    } catch (err) {
        console.error('❌ MongoDB connection error:', err.message);
        console.log('⚠️ Retrying in 5 seconds...');
        setTimeout(connectDB, 5000);
    }
};

connectDB();

// Enhanced Middleware with better error handling
bot.use(async (ctx, next) => {
    try {
        if (!ctx.from) {
            console.warn('⚠️ No user found in context');
            return;
        }
        
        const telegramId = ctx.from.id.toString();
        let user = await User.findOne({ telegramId });
        
        if (!user) {
            user = new User({
                telegramId: telegramId,
                username: ctx.from.username,
                firstName: ctx.from.first_name,
                lastName: ctx.from.last_name,
                isAdmin: ADMIN_IDS.includes(telegramId)
            });
            await user.save();
        }
        
        // Check if user is blocked
        if (user.isBlocked && user.blockedUntil > new Date()) {
            const hoursLeft = Math.ceil((user.blockedUntil - new Date()) / (1000 * 60 * 60));
            await ctx.reply(`🚫 You are blocked for ${hoursLeft} more hours. Please focus on your studies.`);
            return;
        }
        
        // Unblock if time has passed
        if (user.isBlocked && user.blockedUntil <= new Date()) {
            user.isBlocked = false;
            user.messageCount = 0;
            await user.save();
        }
        
        // Track messages for non-admin users
        if (ctx.message && !user.isAdmin) {
            const now = new Date();
            const lastMessageTime = user.lastMessageTime || now;
            const timeDiff = now - lastMessageTime;
            
            if (timeDiff > 5 * 60 * 1000) {
                user.messageCount = 0;
            }
            
            user.messageCount += 1;
            user.lastMessageTime = now;
            
            if (user.messageCount > 5 && !user.stream) {
                user.isBlocked = true;
                user.blockedUntil = new Date(Date.now() + 24 * 60 * 60 * 1000);
                await user.save();
                await ctx.reply('🚫 You have been blocked for 24 hours for spamming. Please focus on your studies.');
                return;
            }
            
            if (user.messageCount === 3 && !user.stream) {
                await ctx.reply('⚠️ Please focus on selecting your study materials. Too many random messages may result in a block.');
            }
            
            await user.save();
        }
        
        ctx.user = user;
        await next();
    } catch (error) {
        console.error('❌ Middleware error:', error.message);
        // Don't break the flow, continue to next middleware
        await next();
    }
});

bot.use(session());

// Keyboards (keep as before)
const languageKeyboard = Markup.keyboard([
    ['🇮🇳 Hindi', '🇬🇧 English']
]).resize();

const streamKeyboard = Markup.keyboard([
    ['Non-Medical', 'Medical'],
    ['Commerce']
]).resize();

const nonMedicalSubjects = Markup.keyboard([
    ['Mathematics', 'Physics'],
    ['Chemistry', 'English']
]).resize();

const medicalSubjects = Markup.keyboard([
    ['Biology', 'Chemistry'],
    ['Physics', 'English']
]).resize();

const commerceSubjects = Markup.keyboard([
    ['Accountancy', 'Business Studies'],
    ['Economics', 'English'],
    ['Mathematics', 'Physical Education'],
    ['Entrepreneurship']
]).resize();

const contentTypeKeyboard = Markup.keyboard([
    ['📹 Lecture (MP4)', '📝 DPP'],
    ['📘 Notes (PDF)', '◀️ Back to Chapters']
]).resize();

const adminKeyboard = Markup.keyboard([
    ['➕ Add Chapter', '📚 View Chapters'],
    ['📁 Add Content', '👥 View Users'],
    ['🏠 Main Menu']
]).resize();

// Enhanced Start Command with error handling
bot.start(async (ctx) => {
    try {
        const user = ctx.user;
        
        user.stream = null;
        user.subject = null;
        user.currentChapter = null;
        await user.save();
        
        await ctx.replyWithPhoto(
            { 
                url: 'https://images.unsplash.com/photo-1501504905252-473c47e087f8?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80',
                filename: 'welcome.jpg'
            },
            {
                caption: `👋 Hello! My name is **Board Booster** created by **Team Hackers**.\n\n📚 Please choose your language first:`,
                parse_mode: 'Markdown',
                reply_markup: languageKeyboard.reply_markup
            }
        );
    } catch (error) {
        console.error('❌ Start command error:', error);
        await ctx.reply('❌ An error occurred. Please try /start again.');
    }
});

// Language Selection with error handling
bot.hears(['🇮🇳 Hindi', '🇬🇧 English'], async (ctx) => {
    try {
        const user = ctx.user;
        const language = ctx.message.text.includes('Hindi') ? 'hindi' : 'english';
        
        user.language = language;
        await user.save();
        
        const greeting = language === 'hindi' 
            ? '✅ आपकी भाषा हिंदी चुनी गई है।\n\n🎓 कृपया अपना स्ट्रीम चुनें:'
            : '✅ You have selected English.\n\n🎓 Please choose your stream:';
        
        await ctx.reply(greeting, { reply_markup: streamKeyboard.reply_markup });
    } catch (error) {
        console.error('❌ Language selection error:', error);
        await ctx.reply('❌ Error processing your selection. Please try again.');
    }
});

// [Rest of your existing handlers remain the same, but wrap each in try-catch]
// For brevity, I'll show the pattern for one more handler:

// Stream Selection with error handling
bot.hears(['Non-Medical', 'Medical', 'Commerce'], async (ctx) => {
    try {
        const user = ctx.user;
        const stream = ctx.message.text;
        
        user.stream = stream;
        await user.save();
        
        let message = '';
        let keyboard;
        
        if (stream === 'Non-Medical') {
            message = user.language === 'hindi' 
                ? '🔬 नॉन-मेडिकल स्ट्रीम चुना गया है।\n\n📚 कृपया विषय चुनें:'
                : '🔬 Non-Medical stream selected.\n\n📚 Please choose your subject:';
            keyboard = nonMedicalSubjects;
        } else if (stream === 'Medical') {
            message = user.language === 'hindi'
                ? '💊 मेडिकल स्ट्रीम चुना गया है।\n\n📚 कृपया विषय चुनें:'
                : '💊 Medical stream selected.\n\n📚 Please choose your subject:';
            keyboard = medicalSubjects;
        } else if (stream === 'Commerce') {
            message = user.language === 'hindi'
                ? '💰 कॉमर्स स्ट्रीम चुना गया है।\n\n📚 कृपया विषय चुनें:'
                : '💰 Commerce stream selected.\n\n📚 Please choose your subject:';
            keyboard = commerceSubjects;
        }
        
        await ctx.reply(message, { reply_markup: keyboard.reply_markup });
    } catch (error) {
        console.error('❌ Stream selection error:', error);
        await ctx.reply('❌ Error processing stream selection. Please try again.');
    }
});

// IMPORTANT: Wrap all your existing handlers in try-catch blocks
// Follow the same pattern for all handlers like:
// bot.hears(...) → wrap in try-catch
// bot.action(...) → wrap in try-catch
// bot.on(...) → wrap in try-catch

// Auto-unblock users every hour
cron.schedule('0 * * * *', async () => {
    try {
        const now = new Date();
        const blockedUsers = await User.find({
            isBlocked: true,
            blockedUntil: { $lte: now }
        });
        
        for (const user of blockedUsers) {
            user.isBlocked = false;
            user.messageCount = 0;
            await user.save();
            
            try {
                await bot.telegram.sendMessage(user.telegramId, 
                    '✅ Your block has been lifted. Please focus on your studies.'
                );
            } catch (error) {
                console.error('Error sending unblock message:', error.message);
            }
        }
        
        if (blockedUsers.length > 0) {
            console.log(`🔄 Auto-unblocked ${blockedUsers.length} users`);
        }
    } catch (error) {
        console.error('❌ Cron job error:', error);
    }
});

// Enhanced error handling
bot.catch((err, ctx) => {
    console.error(`❌ Global error for ${ctx.updateType}:`, err.message);
    
    // Don't send error message to user if it's a network/timeout error
    if (!err.message.includes('ETIMEDOUT') && !err.message.includes('ECONNREFUSED')) {
        try {
            ctx.reply('❌ An unexpected error occurred. Please try again later.').catch(e => {
                console.error('Even error reply failed:', e.message);
            });
        } catch (e) {
            // Ignore if we can't send error message
        }
    }
});

// Handle process errors
process.on('unhandledRejection', (error) => {
    console.error('❌ Unhandled Promise Rejection:', error.message);
});

process.on('uncaughtException', (error) => {
    console.error('❌ Uncaught Exception:', error.message);
});

// FIX FOR RAILWAY: Webhook or Polling based on environment
const startBot = async () => {
    try {
        // Clear any existing webhook first
        await bot.telegram.deleteWebhook();
        console.log('✅ Webhook cleared');
        
        // Get bot info to verify token
        const botInfo = await bot.telegram.getMe();
        console.log(`✅ Bot @${botInfo.username} authenticated`);
        
        if (RAILWAY_ENVIRONMENT || process.env.NODE_ENV === 'production') {
            // Use webhooks for Railway
            const webhookPath = `/webhook/${BOT_TOKEN}`;
            const webhookUrl = `https://${process.env.RAILWAY_STATIC_URL || 'localhost:3000'}${webhookPath}`;
            
            await bot.telegram.setWebhook(webhookUrl);
            console.log(`✅ Webhook set to: ${webhookUrl}`);
            
            // Start webhook
            bot.startWebhook(webhookPath, null, PORT);
            console.log('🚀 Bot running with webhooks on Railway');
        } else {
            // Use polling for local development
            await bot.launch();
            console.log('🚀 Bot running with polling locally');
        }
        
        console.log('👨‍💻 Created by Team Hackers');
        console.log(`📡 Mode: ${RAILWAY_ENVIRONMENT ? 'Webhook (Railway)' : 'Polling (Local)'}`);
        
    } catch (error) {
        console.error('❌ Failed to start bot:', error.message);
        
        // Check if it's the "multiple instances" error
        if (error.response?.error_code === 409) {
            console.error('\n⚠️ IMPORTANT: Bot is already running elsewhere!');
            console.error('💡 Solutions:');
            console.error('1. Stop local terminal running the bot');
            console.error('2. Check other hosting platforms (Vercel, Heroku, etc.)');
            console.error('3. Wait 2 minutes and restart');
        }
        
        process.exit(1);
    }
};

// Start HTTP server first
const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`✅ Health check server running on port ${PORT}`);
    console.log(`🌐 Health endpoint: http://0.0.0.0:${PORT}/health`);
    
    // Then start bot after server is ready
    setTimeout(startBot, 1000);
});

// Graceful shutdown
const shutdown = async (signal) => {
    console.log(`\n🛑 Received ${signal}, shutting down gracefully...`);
    
    try {
        await bot.stop();
        console.log('✅ Bot stopped');
        
        server.close(() => {
            console.log('✅ HTTP server closed');
            process.exit(0);
        });
        
        // Force exit after 10 seconds
        setTimeout(() => {
            console.log('⚠️ Force shutdown after timeout');
            process.exit(1);
        }, 10000);
        
    } catch (error) {
        console.error('❌ Error during shutdown:', error);
        process.exit(1);
    }
};

process.once('SIGINT', () => shutdown('SIGINT'));
process.once('SIGTERM', () => shutdown('SIGTERM'));

// Export for Railway
module.exports = app;
