
import { API_BASE } from "@/utils/constants";
import { baseHeaders } from "@/utils/request";

const Audit = {
    getLogs: async function (workspaceId, filters = {}, limit = 100, offset = 0) {
        const params = new URLSearchParams({
            workspace_id: workspaceId,
            limit,
            offset,
            ...filters,
        });

        return await fetch(`${API_BASE}/v1/audit?${params.toString()}`, {
            method: "GET",
            headers: baseHeaders(),
        })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to fetch audit logs");
                return res.json();
            })
            .catch((e) => {
                console.error(e);
                return [];
            });
    },
};

export default Audit;
