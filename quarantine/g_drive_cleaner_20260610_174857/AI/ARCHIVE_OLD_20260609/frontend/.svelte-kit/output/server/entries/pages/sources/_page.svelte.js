import "../../../chunks/dev.js";
//#region src/routes/sources/+page.svelte
function _page($$renderer) {
	$$renderer.push(`<section class="page"><div class="page-header"><div><p class="eyebrow">Sources</p> <h1>Connaissance</h1> <p class="lead">Les sources sont le point d’entrée simple pour les documents, le web et la mémoire. RAG, chunks et embeddings restent derrière.</p></div> <button class="button primary">Ajouter une source</button></div> <div class="grid grid-3"><div class="card metric"><span class="metric-label">Documents</span> <span class="metric-value">À relier</span> <span class="small muted">Sources locales</span></div> <div class="card metric"><span class="metric-label">Index RAG</span> <span class="metric-value">Prêt</span> <span class="small muted">Connexion détaillée à venir</span></div> <div class="card metric"><span class="metric-label">Web</span> <span class="metric-value">Prévu</span> <span class="small muted">Crawl4AI recommandé</span></div></div> <div class="card"><h2>Approche retenue</h2> <p class="muted">L’utilisateur ajoute une source. Le système se charge ensuite du nettoyage, découpage, indexation et rattachement aux réponses.</p></div></section>`);
}
//#endregion
export { _page as default };
