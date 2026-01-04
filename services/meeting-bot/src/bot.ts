import express from 'express';
// import puppeteer from 'puppeteer-extra';
// import StealthPlugin from 'puppeteer-extra-plugin-stealth';
// puppeteer.use(StealthPlugin());
import puppeteer from 'puppeteer';
import { getStream } from 'puppeteer-stream';
import { S3Client } from '@aws-sdk/client-s3';
import { Upload } from '@aws-sdk/lib-storage';
import Redis from 'ioredis';
import { v4 as uuidv4 } from 'uuid';
import { PassThrough } from 'stream';
import path from 'path';

// Resolve puppeteer-stream extension path
const streamExtensionPath = path.join(path.dirname(require.resolve("puppeteer-stream")), "extension");


// puppeteer.use(StealthPlugin());

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3002;
const REDIS_URL = process.env.REDIS_URL || 'redis://redis:6379';
const S3_ENDPOINT = process.env.S3_ENDPOINT || 'http://minio:9000';
const S3_BUCKET = process.env.S3_BUCKET || 'pandora-audio';
const AWS_REGION = process.env.AWS_REGION || 'us-east-1';
const AWS_ACCESS_KEY_ID = process.env.AWS_ACCESS_KEY_ID || 'minio';
const AWS_SECRET_ACCESS_KEY = process.env.AWS_SECRET_ACCESS_KEY || 'minio123';

const redis = new Redis(REDIS_URL);
const s3 = new S3Client({
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

    const meeting_id = meeting_meta?.id || uuidv4();
    console.log(`[MeetingBot] Received request to join: ${url} (ID: ${meeting_id})`);

    // Respond immediately (Accepted)
    res.status(202).json({ meeting_id, status: 'joining' });

    // Start async processing
    joinAndStream(url, layer_id, meeting_id, meeting_meta).catch(err => {
        console.error(`[MeetingBot] Error in joinAndStream:`, err);
    });
});

async function joinAndStream(url: string, layer_id: string, meeting_id: string, meeting_meta: any) {
    let browser;
    try {
        console.log(`[MeetingBot] Launching browser...`);
        // Use launch from puppeteer-stream directly
        // Pass options directly, no extra wrapper
        browser = await puppeteer.launch({
            executablePath: '/usr/bin/google-chrome',
            headless: false, // Running in Xvfb
            dumpio: true,
            args: [
                '--disable-gpu',
                '--no-zygote',
                // '--single-process', // Often causes issues with extensions, try without first or keep if desperate
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
        const stream = await getStream(page as any, { audio: true, video: false });

        const passThrough = new PassThrough();
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

        const upload = new Upload({
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

    } catch (error) {
        console.error(`[MeetingBot] Fatal error:`, error);
    } finally {
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
