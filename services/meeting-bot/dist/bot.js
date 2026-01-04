"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
// import puppeteer from 'puppeteer-extra';
// import StealthPlugin from 'puppeteer-extra-plugin-stealth';
// puppeteer.use(StealthPlugin());
const puppeteer_1 = __importDefault(require("puppeteer"));
const puppeteer_stream_1 = require("puppeteer-stream");
const client_s3_1 = require("@aws-sdk/client-s3");
const lib_storage_1 = require("@aws-sdk/lib-storage");
const ioredis_1 = __importDefault(require("ioredis"));
const uuid_1 = require("uuid");
const stream_1 = require("stream");
const path_1 = __importDefault(require("path"));
// Resolve puppeteer-stream extension path
const streamExtensionPath = path_1.default.join(path_1.default.dirname(require.resolve("puppeteer-stream")), "extension");
// puppeteer.use(StealthPlugin());
const app = (0, express_1.default)();
app.use(express_1.default.json());
const PORT = process.env.PORT || 3002;
const REDIS_URL = process.env.REDIS_URL || 'redis://redis:6379';
const S3_ENDPOINT = process.env.S3_ENDPOINT || 'http://minio:9000';
const S3_BUCKET = process.env.S3_BUCKET || 'pandora-audio';
const AWS_REGION = process.env.AWS_REGION || 'us-east-1';
const AWS_ACCESS_KEY_ID = process.env.AWS_ACCESS_KEY_ID || 'minio';
const AWS_SECRET_ACCESS_KEY = process.env.AWS_SECRET_ACCESS_KEY || 'minio123';
const redis = new ioredis_1.default(REDIS_URL);
const s3 = new client_s3_1.S3Client({
    endpoint: S3_ENDPOINT,
    region: AWS_REGION,
    credentials: {
        accessKeyId: AWS_ACCESS_KEY_ID,
        secretAccessKey: AWS_SECRET_ACCESS_KEY,
    },
    forcePathStyle: true,
});
app.post('/join', async (req, res) => {
    const { url, layer_id, meeting_meta } = req.body;
    if (!url || !layer_id) {
        return res.status(400).json({ error: 'Missing url or layer_id' });
    }
    const meeting_id = meeting_meta?.id || (0, uuid_1.v4)();
    console.log(`[MeetingBot] Received request to join: ${url} (ID: ${meeting_id})`);
    // Respond immediately (Accepted)
    res.status(202).json({ meeting_id, status: 'joining' });
    // Start async processing
    joinAndStream(url, layer_id, meeting_id, meeting_meta).catch(err => {
        console.error(`[MeetingBot] Error in joinAndStream:`, err);
    });
});
async function joinAndStream(url, layer_id, meeting_id, meeting_meta) {
    let browser;
    try {
        console.log(`[MeetingBot] Launching browser...`);
        // Use launch from puppeteer-stream directly
        // Pass options directly, no extra wrapper
        browser = await puppeteer_1.default.launch({
            executablePath: '/usr/bin/google-chrome',
            headless: false, // Running in Xvfb
            dumpio: true,
            args: [
                '--disable-gpu',
                `--load-extension=${streamExtensionPath}`,
                `--disable-extensions-except=${streamExtensionPath}`,
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--use-fake-ui-for-media-stream',
                '--autoplay-policy=no-user-gesture-required',
                '--start-maximized',
                '--window-size=1280,720'
            ],
            defaultViewport: null,
        });
        const page = await browser.newPage();
        // Basic navigation and "joining" logic (Simplified for MVP)
        // Real implementation needs specific selectors for Zoom/Teams/Meet
        console.log(`[MeetingBot] Navigating to ${url}...`);
        await page.goto(url, { waitUntil: 'networkidle2' });
        // TODO: Add platform-specific logic here (clicking "Join", entering name, etc.)
        // For now, we assume a direct streamable page or simple click-through
        // await handlePlatformSpecifics(page, url);
        console.log(`[MeetingBot] Capturing audio stream...`);
        const stream = await (0, puppeteer_stream_1.getStream)(page, { audio: true, video: false });
        const passThrough = new stream_1.PassThrough();
        stream.pipe(passThrough);
        // Stop recording after duration (default 15s for MVP/Testing)
        const durationSeconds = meeting_meta?.duration || 15;
        console.log(`[MeetingBot] Recording for ${durationSeconds} seconds...`);
        setTimeout(() => {
            console.log(`[MeetingBot] Duration reached. Stopping stream.`);
            stream.destroy();
            passThrough.end(); // Make sure S3 knows it's the end
        }, durationSeconds * 1000);
        const s3Key = `${layer_id}/${meeting_id}.webm`;
        console.log(`[MeetingBot] Streaming to S3: s3://${S3_BUCKET}/${s3Key}`);
        const upload = new lib_storage_1.Upload({
            client: s3,
            params: {
                Bucket: S3_BUCKET,
                Key: s3Key,
                Body: passThrough,
                ContentType: 'audio/webm',
            },
            partSize: 5 * 1024 * 1024, // 5MB parts
            queueSize: 4,
        });
        upload.on('httpUploadProgress', (progress) => {
            console.log(`[MeetingBot] Upload progress: ${progress.loaded} bytes`);
        });
        await upload.done();
        console.log(`[MeetingBot] Stream upload complete.`);
        // Notify Cortex via Redis
        const payload = {
            s3_key: s3Key,
            layer_id,
            meeting_meta: { ...meeting_meta, id: meeting_id },
        };
        await redis.lpush('audio_processing_queue', JSON.stringify(payload));
        console.log(`[MeetingBot] Pushed job to Redis: audio_processing_queue`);
    }
    catch (error) {
        console.error(`[MeetingBot] Fatal error:`, error);
    }
    finally {
        if (browser) {
            // Ensure browser closes after a reasonable time or on specific triggers
            // For MVP, we might keep it open for a set duration or until the stream ends
            // But getStream usually ends when the page closes or stream ends.
            await browser.close();
        }
    }
}
app.listen(PORT, () => {
    console.log(`[MeetingBot] Listening on port ${PORT}`);
});
