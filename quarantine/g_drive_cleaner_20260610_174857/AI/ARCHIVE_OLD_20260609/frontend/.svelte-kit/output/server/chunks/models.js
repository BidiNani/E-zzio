//#region src/lib/data/models.js
var recommendedModels = [
	{
		name: "qwen3:4b",
		role: "Rapide",
		mode: "fast",
		required: true,
		description: "Réponses courtes, tâches simples, usage quotidien."
	},
	{
		name: "qwen3:8b",
		role: "RAG / Raisonnement",
		mode: "rag",
		required: true,
		description: "Synthèse et raisonnement avec sources."
	},
	{
		name: "deepseek-r1:8b",
		role: "Raisonnement",
		mode: "reason",
		required: true,
		description: "Analyse, planification, autonomie."
	},
	{
		name: "qwen2.5-coder:7b",
		role: "Code",
		mode: "code",
		required: true,
		description: "Scripts, patchs, refactor, PowerShell et Python."
	},
	{
		name: "nomic-embed-text",
		role: "Embeddings",
		mode: "embedding",
		required: true,
		description: "Indexation RAG et recherche documentaire."
	},
	{
		name: "shieldgemma:2b",
		role: "Sécurité",
		mode: "safety",
		required: true,
		description: "Garde-fous et filtrage sécurité."
	},
	{
		name: "gemma4:e4b",
		role: "Qualité",
		mode: "quality",
		required: false,
		description: "Synthèse finale et relecture premium. À benchmarker CPU."
	}
];
function mergeModelRegistry(installedModels = []) {
	const installedNames = new Set(installedModels.map((model) => String(model.name ?? model.model ?? model.id ?? model).trim()));
	return recommendedModels.map((model) => ({
		...model,
		installed: installedNames.has(model.name),
		status: installedNames.has(model.name) ? "Prêt" : model.required ? "Manquant" : "Optionnel"
	}));
}
//#endregion
export { mergeModelRegistry as t };
