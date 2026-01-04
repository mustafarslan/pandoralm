/**
 * Cortex Client - API wrapper for Pandora Cortex backend
 * 
 * This module provides methods to call Cortex APIs from the Node.js layer.
 * All vector/embedding operations should go through Cortex to ensure
 * consistent embedding models and knowledge layer security.
 */

const CORTEX_BASE_URL = process.env.CORTEX_URL || "http://pandora-cortex:8000";

const CortexClient = {
    /**
     * Performs a semantic similarity search via Cortex.
     * This replaces local LanceDB searches to avoid embedding model mismatches.
     * 
     * @param {Object} params
     * @param {string} params.query - The user's query text
     * @param {string} params.workspaceId - The workspace ID (used as LanceDB table namespace)
     * @param {number} params.topK - Number of results to return
     * @param {string[]} params.documentIds - Optional filter by document IDs
     * @param {string[]} params.allowedLayers - Optional knowledge layer IDs for ReBAC filtering
     * @returns {Promise<{contextTexts: string[], sources: object[], message: string|null}>}
     */
    performSimilaritySearch: async function ({
        query,
        workspaceId,
        topK = 4,
        documentIds = [],
        allowedLayers = [],
    }) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

        try {
            console.log(`[CortexClient] Searching workspace: ${workspaceId} query: "${query.slice(0, 50)}..."`);
            const start = Date.now();

            const response = await fetch(`${CORTEX_BASE_URL}/api/v1/vectors/search`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    query,
                    workspace_id: workspaceId,
                    top_k: topK,
                    document_ids: documentIds.length > 0 ? documentIds : null,
                    allowed_layers: allowedLayers.length > 0 ? allowedLayers : null,
                }),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[CortexClient] Search failed: ${response.status} - ${errorText}`);
                return {
                    contextTexts: [],
                    sources: [],
                    message: `Cortex search failed: ${response.status}`,
                };
            }

            const results = await response.json();
            console.log(`[CortexClient] Search completed in ${Date.now() - start}ms. Found ${results.length} results.`);

            // Transform Cortex response to match expected format
            const contextTexts = [];
            const sources = [];

            for (const result of results) {
                const chunk = result.chunk;
                contextTexts.push(chunk.content);
                sources.push({
                    text: chunk.content.slice(0, 1000) + (chunk.content.length > 1000 ? "...continued in source..." : ""),
                    title: chunk.metadata?.title || "Unknown",
                    ...chunk.metadata,
                    score: result.score,
                });
            }

            return {
                contextTexts,
                sources,
                message: null,
            };
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                console.error("[CortexClient] Search timed out after 30s");
                return {
                    contextTexts: [],
                    sources: [],
                    message: "Vector search timed out",
                };
            }
            console.error("[CortexClient] performSimilaritySearch error:", error.message);
            return {
                contextTexts: [],
                sources: [],
                message: `Cortex connection error: ${error.message}`,
            };
        }
    },

    /**
     * Gets the vector count for a workspace via Cortex.
     * @param {string} workspaceId
     * @returns {Promise<number>}
     */
    getVectorCount: async function (workspaceId) {
        try {
            const response = await fetch(
                `${CORTEX_BASE_URL}/api/v1/vectors/collections/${encodeURIComponent(workspaceId)}`,
                { method: "GET" }
            );

            if (!response.ok) return 0;

            const stats = await response.json();
            return stats.total_chunks || 0;
        } catch (error) {
            console.error("[CortexClient] getVectorCount error:", error.message);
            return 0;
        }
    },

    /**
     * Checks if a workspace has any vectors via Cortex.
     * @param {string} workspaceId
     * @returns {Promise<boolean>}
     */
    hasVectors: async function (workspaceId) {
        const count = await this.getVectorCount(workspaceId);
        return count > 0;
    },

    /**
     * Proxies the chat stream from Cortex Cognitive Router.
     * @param {Object} params
     * @param {string} params.query
     * @param {string} params.workspaceId
     * @param {string} params.mode - "auto", "vector", "graph", "hybrid", "research"
     * @returns {Promise<Response>} - The fetch Response object (stream)
     */
    chat: async function ({ query, workspaceId, mode = "auto" }) {
        try {
            const response = await fetch(`${CORTEX_BASE_URL}/api/v1/stream/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, workspace_id: workspaceId, mode }),
            });
            return response;
        } catch (error) {
            console.error("[CortexClient] chat error:", error.message);
            throw error;
        }
    },

    /**
     * Deletes a workspace and its data (Vectors + Graph) via Cortex.
     * @param {string} workspaceId
     * @returns {Promise<boolean>}
     */
    deleteWorkspace: async function (workspaceId) {
        try {
            const response = await fetch(
                `${CORTEX_BASE_URL}/api/v1/vectors/collections/${encodeURIComponent(workspaceId)}`,
                { method: "DELETE" }
            );
            return response.ok;
        } catch (error) {
            console.error("[CortexClient] deleteWorkspace error:", error.message);
            return false;
        }
    },
};

module.exports = { CortexClient };
