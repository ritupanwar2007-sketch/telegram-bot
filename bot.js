const express = require('express');
const { Telegraf, Markup, session } = require('telegraf');
const mongoose = require('mongoose');
const cron = require('node-cron');
require('dotenv').config();

// Initialize Express for Railway health checks
const app = express();
const PORT = process.env.PORT || 3000;

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
        uptime: process.uptime()
    });
});

// Start health check server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`✅ Health check server running on port ${PORT}`);
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

if (!BOT_TOKEN) {
    console.error('❌ BOT_TOKEN is required!');
    process.exit(1);
}

// Initialize bot
const bot = new Telegraf(BOT_TOKEN);

// MongoDB Connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/boardbooster', {
    useNewUrlParser: true,
    useUnifiedTopology: true
}).then(() => {
    console.log('✅ Connected to MongoDB');
}).catch(err => {
    console.error('❌ MongoDB connection error:', err);
});

// Middleware
bot.use(async (ctx, next) => {
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
});

bot.use(session());

// Keyboards
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

// Start Command
bot.start(async (ctx) => {
    const user = ctx.user;
    
    user.stream = null;
    user.subject = null;
    user.currentChapter = null;
    await user.save();
    
    await ctx.replyWithPhoto(
        { url: 'https://images.unsplash.com/photo-1501504905252-473c47e087f8?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80' },
        {
            caption: `👋 Hello! My name is **Board Booster** created by **Team Hackers**.\n\n📚 Please choose your language first:`,
            parse_mode: 'Markdown',
            reply_markup: languageKeyboard.reply_markup
        }
    );
});

// Language Selection
bot.hears(['🇮🇳 Hindi', '🇬🇧 English'], async (ctx) => {
    const user = ctx.user;
    const language = ctx.message.text.includes('Hindi') ? 'hindi' : 'english';
    
    user.language = language;
    await user.save();
    
    const greeting = language === 'hindi' 
        ? '✅ आपकी भाषा हिंदी चुनी गई है।\n\n🎓 कृपया अपना स्ट्रीम चुनें:'
        : '✅ You have selected English.\n\n🎓 Please choose your stream:';
    
    await ctx.reply(greeting, { reply_markup: streamKeyboard.reply_markup });
});

// Stream Selection
bot.hears(['Non-Medical', 'Medical', 'Commerce'], async (ctx) => {
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
});

// Subject Selection Handler
const subjects = {
    'Non-Medical': ['Mathematics', 'Physics', 'Chemistry', 'English'],
    'Medical': ['Biology', 'Chemistry', 'Physics', 'English'],
    'Commerce': ['Accountancy', 'Business Studies', 'Economics', 'English', 'Mathematics', 'Physical Education', 'Entrepreneurship']
};

bot.hears([...subjects['Non-Medical'], ...subjects['Medical'], ...subjects['Commerce']], async (ctx) => {
    const user = ctx.user;
    const subject = ctx.message.text;
    
    if (!user.stream || !subjects[user.stream]?.includes(subject)) {
        await ctx.reply('❌ Please select a valid subject for your stream.');
        return;
    }
    
    user.subject = subject;
    await user.save();
    
    const chapters = await Chapter.find({ stream: user.stream, subject: subject });
    
    if (chapters.length === 0) {
        const message = user.language === 'hindi'
            ? `📖 आपने **${subject}** चुना है।\n\n⚠️ अभी तक कोई अध्याय उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।`
            : `📖 You have selected **${subject}**.\n\n⚠️ No chapters are available yet. Please check back later.`;
        await ctx.reply(message, { parse_mode: 'Markdown' });
        return;
    }
    
    const chapterButtons = chapters.map(chapter => 
        [Markup.button.callback(chapter.chapterName, `chapter_${chapter._id}`)]
    );
    chapterButtons.push([Markup.button.callback('◀️ Back to Subjects', 'back_to_subjects')]);
    
    const chapterKeyboard = Markup.inlineKeyboard(chapterButtons);
    
    const message = user.language === 'hindi'
        ? `📖 आपने **${subject}** चुना है।\n\n📚 कृपया अध्याय चुनें:`
        : `📖 You have selected **${subject}**.\n\n📚 Please choose a chapter:`;
    
    await ctx.reply(message, { parse_mode: 'Markdown', reply_markup: chapterKeyboard });
});

// Chapter Selection
bot.action(/chapter_(.+)/, async (ctx) => {
    const chapterId = ctx.match[1];
    const user = ctx.user;
    
    const chapter = await Chapter.findById(chapterId);
    if (!chapter) {
        await ctx.answerCbQuery('❌ Chapter not found');
        return;
    }
    
    user.currentChapter = chapterId;
    await user.save();
    
    const message = user.language === 'hindi'
        ? `📚 आपने **"${chapter.chapterName}"** चुना है।\n\n🎯 कृपया कंटेंट टाइप चुनें:`
        : `📚 You have selected **"${chapter.chapterName}"**.\n\n🎯 Please choose content type:`;
    
    await ctx.editMessageText(message, {
        parse_mode: 'Markdown',
        reply_markup: contentTypeKeyboard.reply_markup
    });
    
    await ctx.answerCbQuery();
});

// Back to Subjects
bot.action('back_to_subjects', async (ctx) => {
    const user = ctx.user;
    
    if (!user.stream) {
        await ctx.answerCbQuery('❌ Please select stream first');
        return;
    }
    
    let keyboard;
    if (user.stream === 'Non-Medical') {
        keyboard = nonMedicalSubjects;
    } else if (user.stream === 'Medical') {
        keyboard = medicalSubjects;
    } else {
        keyboard = commerceSubjects;
    }
    
    const message = user.language === 'hindi'
        ? '📚 कृपया विषय चुनें:'
        : '📚 Please choose your subject:';
    
    await ctx.editMessageText(message, {
        reply_markup: keyboard.reply_markup
    });
    
    await ctx.answerCbQuery();
});

// Content Type Selection
bot.hears(['📹 Lecture (MP4)', '📝 DPP', '📘 Notes (PDF)'], async (ctx) => {
    const user = ctx.user;
    const contentType = ctx.message.text.includes('Lecture') ? 'lecture' 
        : ctx.message.text.includes('DPP') ? 'dpp' 
        : 'notes';
    
    if (!user.currentChapter) {
        await ctx.reply('❌ Please select a chapter first.');
        return;
    }
    
    const contents = await Content.find({
        chapterId: user.currentChapter,
        contentType: contentType
    }).populate('chapterId');
    
    if (contents.length === 0) {
        const message = user.language === 'hindi'
            ? `⚠️ इस अध्याय के लिए ${contentType} उपलब्ध नहीं है।`
            : `⚠️ No ${contentType} available for this chapter yet.`;
        await ctx.reply(message);
        return;
    }
    
    for (const content of contents) {
        try {
            if (contentType === 'lecture') {
                await ctx.replyWithVideo(content.fileId, {
                    caption: content.caption || `🎬 Lecture: ${content.chapterId.chapterName}`,
                    parse_mode: 'Markdown'
                });
            } else {
                await ctx.replyWithDocument(content.fileId, {
                    caption: content.caption || `📄 ${contentType.toUpperCase()}: ${content.chapterId.chapterName}`,
                    parse_mode: 'Markdown'
                });
            }
        } catch (error) {
            console.error('Error sending file:', error);
            await ctx.reply('❌ Error sending file. Please try again.');
        }
    }
    
    await ctx.reply('Select another content type or go back:', {
        reply_markup: contentTypeKeyboard.reply_markup
    });
});

// Back to Chapters
bot.hears('◀️ Back to Chapters', async (ctx) => {
    const user = ctx.user;
    
    if (!user.stream || !user.subject) {
        await ctx.reply('❌ Please select stream and subject first.');
        return;
    }
    
    const chapters = await Chapter.find({ stream: user.stream, subject: user.subject });
    
    if (chapters.length === 0) {
        await ctx.reply('📭 No chapters available.');
        return;
    }
    
    const chapterButtons = chapters.map(chapter => 
        [Markup.button.callback(chapter.chapterName, `chapter_${chapter._id}`)]
    );
    
    const chapterKeyboard = Markup.inlineKeyboard(chapterButtons);
    
    await ctx.reply('📚 Please choose a chapter:', { reply_markup: chapterKeyboard });
});

// Admin Panel
bot.command('admin', async (ctx) => {
    const user = ctx.user;
    
    if (!user.isAdmin) {
        await ctx.reply('🚫 You are not authorized to access admin panel.');
        return;
    }
    
    await ctx.reply('🔧 **Admin Panel**', { 
        parse_mode: 'Markdown',
        reply_markup: adminKeyboard.reply_markup 
    });
});

// Admin: Add Chapter
bot.hears('➕ Add Chapter', async (ctx) => {
    const user = ctx.user;
    
    if (!user.isAdmin) return;
    
    ctx.session = { ...ctx.session, adminAction: 'add_chapter_step1' };
    await ctx.reply('📝 Please select stream:', { reply_markup: streamKeyboard.reply_markup });
});

// Handle admin stream selection
bot.hears(['Non-Medical', 'Medical', 'Commerce'], async (ctx) => {
    const user = ctx.user;
    const session = ctx.session;
    
    if (!user.isAdmin || !session?.adminAction) return;
    
    if (session.adminAction === 'add_chapter_step1') {
        session.stream = ctx.message.text;
        session.adminAction = 'add_chapter_step2';
        
        let keyboard;
        if (session.stream === 'Non-Medical') {
            keyboard = nonMedicalSubjects;
        } else if (session.stream === 'Medical') {
            keyboard = medicalSubjects;
        } else {
            keyboard = commerceSubjects;
        }
        
        await ctx.reply(`📁 Stream: **${session.stream}**\n\n📚 Please select subject:`, {
            parse_mode: 'Markdown',
            reply_markup: keyboard.reply_markup
        });
    }
});

// Handle admin subject selection
bot.hears([...subjects['Non-Medical'], ...subjects['Medical'], ...subjects['Commerce']], async (ctx) => {
    const user = ctx.user;
    const session = ctx.session;
    
    if (!user.isAdmin || !session?.adminAction || session.adminAction !== 'add_chapter_step2') return;
    
    session.subject = ctx.message.text;
    session.adminAction = 'add_chapter_step3';
    
    await ctx.reply(`📁 Stream: **${session.stream}**\n📚 Subject: **${session.subject}**\n\n📝 Please enter chapter name:`, {
        parse_mode: 'Markdown',
        reply_markup: { remove_keyboard: true }
    });
});

// Handle chapter name input
bot.on('text', async (ctx) => {
    const user = ctx.user;
    const session = ctx.session;
    const text = ctx.message.text;
    
    if (user.isAdmin && session?.adminAction === 'add_chapter_step3') {
        const chapter = new Chapter({
            stream: session.stream,
            subject: session.subject,
            chapterName: text,
            addedBy: user.telegramId
        });
        
        await chapter.save();
        
        await ctx.reply(`✅ Chapter **"${text}"** added successfully to ${session.stream} > ${session.subject}!`, {
            parse_mode: 'Markdown',
            reply_markup: adminKeyboard.reply_markup
        });
        
        ctx.session = {};
    }
});

// Admin: View Chapters
bot.hears('📚 View Chapters', async (ctx) => {
    const user = ctx.user;
    
    if (!user.isAdmin) return;
    
    const chapters = await Chapter.find().sort({ stream: 1, subject: 1 });
    
    if (chapters.length === 0) {
        await ctx.reply('📭 No chapters added yet.');
        return;
    }
    
    let message = '📚 **All Chapters:**\n\n';
    let currentStream = '';
    let currentSubject = '';
    
    for (const chapter of chapters) {
        if (chapter.stream !== currentStream) {
            currentStream = chapter.stream;
            currentSubject = '';
            message += `\n📁 **${currentStream}:**\n`;
        }
        
        if (chapter.subject !== currentSubject) {
            currentSubject = chapter.subject;
            message += `  📖 **${currentSubject}:**\n`;
        }
        
        message += `    • ${chapter.chapterName}\n`;
    }
    
    await ctx.reply(message, { 
        parse_mode: 'Markdown',
        reply_markup: adminKeyboard.reply_markup 
    });
});

// Admin: Add Content
bot.hears('📁 Add Content', async (ctx) => {
    const user = ctx.user;
    
    if (!user.isAdmin) return;
    
    const chapters = await Chapter.find();
    
    if (chapters.length === 0) {
        await ctx.reply('❌ No chapters available. Please add chapters first.');
        return;
    }
    
    const chapterButtons = chapters.map(chapter => [
        Markup.button.callback(
            `${chapter.stream} > ${chapter.subject} > ${chapter.chapterName}`,
            `admin_content_${chapter._id}`
        )
    ]);
    
    const keyboard = Markup.inlineKeyboard(chapterButtons);
    
    await ctx.reply('📚 Select a chapter to add content:', { reply_markup: keyboard });
});

// Handle chapter selection for adding content
bot.action(/admin_content_(.+)/, async (ctx) => {
    const chapterId = ctx.match[1];
    const chapter = await Chapter.findById(chapterId);
    
    if (!chapter) {
        await ctx.answerCbQuery('❌ Chapter not found');
        return;
    }
    
    ctx.session = {
        ...ctx.session,
        adminAction: 'add_content',
        selectedChapterId: chapterId
    };
    
    await ctx.editMessageText(
        `✅ Selected: **${chapter.stream} > ${chapter.subject} > ${chapter.chapterName}**\n\n📤 Please send the file:\n• MP4 for lectures\n• PDF for notes/DPP`,
        {
            parse_mode: 'Markdown',
            reply_markup: Markup.inlineKeyboard([
                [Markup.button.callback('📹 Lecture', 'content_type_lecture')],
                [Markup.button.callback('📝 DPP', 'content_type_dpp')],
                [Markup.button.callback('📘 Notes', 'content_type_notes')],
                [Markup.button.callback('❌ Cancel', 'cancel_admin_action')]
            ])
        }
    );
    
    await ctx.answerCbQuery();
});

// Handle content type selection
bot.action(/content_type_(lecture|dpp|notes)/, async (ctx) => {
    const contentType = ctx.match[1];
    ctx.session.contentType = contentType;
    
    await ctx.editMessageText(
        `📁 Content type: **${contentType}**\n\n📤 Now please send the file:${contentType === 'lecture' ? '\n• Send MP4 video' : '\n• Send PDF file'}`
    );
    
    await ctx.answerCbQuery();
});

// Handle file upload
bot.on(['video', 'document'], async (ctx) => {
    const user = ctx.user;
    const session = ctx.session;
    
    if (!user.isAdmin || !session?.adminAction === 'add_content' || !session.contentType) return;
    
    const file = ctx.message.video || ctx.message.document;
    const fileId = file.file_id;
    const fileName = file.file_name || 'untitled';
    
    // Validate file type
    if (session.contentType === 'lecture' && !ctx.message.video) {
        await ctx.reply('❌ Please send a video file for lectures.');
        return;
    }
    
    if ((session.contentType === 'dpp' || session.contentType === 'notes') && !ctx.message.document) {
        await ctx.reply('❌ Please send a PDF file for DPP/Notes.');
        return;
    }
    
    const content = new Content({
        chapterId: session.selectedChapterId,
        contentType: session.contentType,
        fileId: fileId,
        fileName: fileName,
        addedBy: user.telegramId
    });
    
    await content.save();
    
    await ctx.reply(`✅ ${session.contentType.toUpperCase()} added successfully!`, {
        reply_markup: adminKeyboard.reply_markup
    });
    
    ctx.session = {};
});

// Admin: View Users
bot.hears('👥 View Users', async (ctx) => {
    const user = ctx.user;
    
    if (!user.isAdmin) return;
    
    const users = await User.find().sort({ createdAt: -1 }).limit(50);
    
    let message = '👥 **Recent Users (Last 50):**\n\n';
    let userCount = 0;
    let blockedCount = 0;
    
    for (const u of users) {
        userCount++;
        if (u.isBlocked) blockedCount++;
        
        message += `${u.isAdmin ? '👑' : '👤'} **${u.firstName || 'User'}** ${u.username ? `(@${u.username})` : ''}\n`;
        message += `ID: ${u.telegramId}\n`;
        message += `Lang: ${u.language} | Stream: ${u.stream || 'Not selected'}\n`;
        message += `Subj: ${u.subject || 'Not selected'}\n`;
        message += `Msgs: ${u.messageCount} | ${u.isBlocked ? '🚫 Blocked' : '✅ Active'}\n`;
        message += `Joined: ${u.createdAt.toLocaleDateString()}\n`;
        message += '─'.repeat(30) + '\n';
    }
    
    message += `\n📊 **Total:** ${userCount} users | 🚫 **Blocked:** ${blockedCount}`;
    
    await ctx.reply(message, { 
        parse_mode: 'Markdown',
        reply_markup: adminKeyboard.reply_markup 
    });
});

// Cancel admin action
bot.action('cancel_admin_action', async (ctx) => {
    ctx.session = {};
    await ctx.editMessageText('❌ Action cancelled.', {
        reply_markup: adminKeyboard.reply_markup
    });
    await ctx.answerCbQuery();
});

// Main Menu
bot.hears('🏠 Main Menu', async (ctx) => {
    const user = ctx.user;
    
    if (user.isAdmin) {
        await ctx.reply('↩️ Returning to main menu...');
    }
    
    user.stream = null;
    user.subject = null;
    user.currentChapter = null;
    await user.save();
    
    const message = user.language === 'hindi'
        ? '🏠 मुख्य मेनू। कृपया अपनी भाषा चुनें:'
        : '🏠 Main menu. Please choose your language:';
    
    await ctx.reply(message, { reply_markup: languageKeyboard.reply_markup });
});

// Handle random messages
bot.on('text', async (ctx) => {
    const user = ctx.user;
    const text = ctx.message.text;
    
    if (text.startsWith('/') || user.isAdmin) return;
    
    if (!user.language) {
        await ctx.reply('🌐 Please select your language first.', {
            reply_markup: languageKeyboard.reply_markup
        });
        return;
    }
    
    if (!user.stream) {
        await ctx.reply('🎓 Please select your stream.', {
            reply_markup: streamKeyboard.reply_markup
        });
        return;
    }
    
    const warning = user.language === 'hindi'
        ? '⚠️ कृपया अपनी पढ़ाई पर ध्यान दें। यादृच्छिक संदेश भेजने से आपको ब्लॉक किया जा सकता है।'
        : '⚠️ Please focus on your studies. Sending random messages may get you blocked.';
    
    await ctx.reply(warning);
});

// Auto-unblock users every hour
cron.schedule('0 * * * *', async () => {
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
            console.error('Error sending unblock message:', error);
        }
    }
    
    if (blockedUsers.length > 0) {
        console.log(`🔄 Auto-unblocked ${blockedUsers.length} users`);
    }
});

// Error handling
bot.catch((err, ctx) => {
    console.error(`❌ Error for ${ctx.updateType}:`, err);
    ctx.reply('❌ An error occurred. Please try again.');
});

// Start bot
bot.launch().then(() => {
    console.log('🚀 Board Booster Bot is running...');
    console.log('👨‍💻 Created by Team Hackers');
});

// Graceful shutdown
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

// Export for Railway
module.exports = app;
