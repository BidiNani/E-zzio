//#region src/lib/api/client.js
var API_BASE = "http://127.0.0.1:8000";
async function apiRequest(path, options = {}, fallback = null) {
	const controller = new AbortController();
	const timeout = options.timeout ?? 7e3;
	const timer = setTimeout(() => controller.abort(), timeout);
	try {
		const response = await fetch(`${API_BASE}${path}`, {
			method: options.method ?? "GET",
			headers: {
				Accept: "application/json",
				...options.body ? { "Content-Type": "application/json" } : {},
				...options.headers ?? {}
			},
			body: options.body ? JSON.stringify(options.body) : void 0,
			signal: controller.signal
		});
		clearTimeout(timer);
		if (!response.ok) return fallback;
		return await response.json();
	} catch {
		clearTimeout(timer);
		return fallback;
	}
}
function apiGet(path, fallback = null, timeout = 7e3) {
	return apiRequest(path, {
		method: "GET",
		timeout
	}, fallback);
}
async function apiGetFirst(paths, fallback = null, timeout = 7e3) {
	for (const path of paths) {
		const result = await apiGet(path, null, timeout);
		if (result !== null && result !== void 0) return {
			path,
			data: result
		};
	}
	return {
		path: null,
		data: fallback
	};
}
function normalizeArray(value, keys = []) {
	if (Array.isArray(value)) return value;
	if (value && typeof value === "object") {
		for (const key of keys) if (Array.isArray(value[key])) return value[key];
	}
	return [];
}
//#endregion
//#region src/lib/api/status.js
async function getHardwareStatus() {
	return apiGet("/api/hardware/status", null, 7e3);
}
async function getHealthSummary() {
	return await apiGetFirst([
		"/api/health",
		"/api/status",
		"/api/system/health",
		"/api/hardware/status"
	], null, 7e3);
}
async function getModelStatus() {
	return await apiGetFirst([
		"/api/ollama/tags",
		"/api/models",
		"/api/brain/models",
		"/api/model/status",
		"/api/hardware/status"
	], null, 7e3);
}
function extractModels(payload) {
	if (!payload) return [];
	return normalizeArray(payload, [
		"models",
		"data",
		"items",
		"available_models"
	]).map((item) => {
		if (typeof item === "string") return { name: item };
		if (item && typeof item === "object") return {
			...item,
			name: item.name ?? item.model ?? item.id ?? item.title ?? "unknown"
		};
		return null;
	}).filter(Boolean);
}
//#endregion
export { getModelStatus as i, getHardwareStatus as n, getHealthSummary as r, extractModels as t };
