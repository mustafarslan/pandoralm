const { validApiKey } = require("../../../utils/middleware/validApiKey");

function apiOpsEndpoints(router) {
    if (!router) return;

    // Generic Proxy Handler
    const proxyHandler = async (request, response) => {
        try {
            // Default to pandora-cortex:8000 if not set (Docker/K8s defaults)
            const CORTEX_URL = process.env.CORTEX_API_URL || process.env.CORTEX_URL || "http://pandora-cortex:8000";

            // request.originalUrl includes the full path including the mount point
            // e.g. /api/v1/ops/jobs/active if router is mounted at /api
            // Target: http://localhost:8000/api/v1/ops/jobs/active
            // We need to prepend nothing if CORTEX_URL ends with no slash and originalUrl starts with /api
            // CORTEX_URL: http://localhost:8000
            // originalUrl: /api/v1/ops/...
            // Target: http://localhost:8000/api/v1/ops/...

            const targetUrl = `${CORTEX_URL.replace(/\/$/, "")}${request.originalUrl}`;

            console.log(`[Proxy] Forwarding ${request.method} ${request.originalUrl} to ${targetUrl}`);

            const headers = { ...request.headers };
            delete headers["host"];
            delete headers["content-length"];

            const fetchOptions = {
                method: request.method,
                headers: headers,
            };

            if (["POST", "PUT", "PATCH"].includes(request.method) && request.body) {
                fetchOptions.body = JSON.stringify(request.body);
                if (!headers["content-type"]) {
                    headers["content-type"] = "application/json";
                }
            }

            const proxyRes = await fetch(targetUrl, fetchOptions);

            // Forward status
            response.status(proxyRes.status);

            // Forward headers
            proxyRes.headers.forEach((value, key) => {
                response.setHeader(key, value);
            });

            // Forward body
            const data = await proxyRes.arrayBuffer();
            response.send(Buffer.from(data));

        } catch (e) {
            console.error("[Proxy] Link Error:", e);
            response.status(502).json({ error: "Bad Gateway", details: e.message });
        }
    };

    // Mount middleware for Ops and Evaluation routes (Prefix based)
    router.use("/v1/ops", proxyHandler);
    router.use("/v1/evaluation", proxyHandler);
    router.use("/evaluation", proxyHandler); // Legacy route for Quality Gate
    router.use("/v1/system/models", proxyHandler);
}

module.exports = { apiOpsEndpoints };
