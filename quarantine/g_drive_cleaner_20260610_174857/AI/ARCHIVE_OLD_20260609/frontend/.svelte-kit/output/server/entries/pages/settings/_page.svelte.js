import "../../../chunks/dev.js";
//#region src/routes/settings/+page.svelte
function _page($$renderer) {
	$$renderer.push(`<section class="page"><div class="page-header"><div><p class="eyebrow">Réglages</p> <h1>Préférences</h1> <p class="lead">Réglages simples. Les options avancées pourront être ajoutées sans encombrer l’interface.</p></div></div> <div class="grid grid-2"><div class="card"><h2>Interface</h2> <div class="stack"><label><span class="small muted">Thème</span> <select class="select">`);
	$$renderer.option({}, ($$renderer) => {
		$$renderer.push(`Clair professionnel`);
	});
	$$renderer.option({ disabled: true }, ($$renderer) => {
		$$renderer.push(`Sombre doux — plus tard`);
	});
	$$renderer.push(`</select></label> <label><span class="small muted">Mode par défaut</span> <select class="select">`);
	$$renderer.option({}, ($$renderer) => {
		$$renderer.push(`Automatique`);
	});
	$$renderer.option({}, ($$renderer) => {
		$$renderer.push(`Rapide`);
	});
	$$renderer.option({}, ($$renderer) => {
		$$renderer.push(`Qualité`);
	});
	$$renderer.push(`</select></label></div></div> <div class="card"><h2>Connexion</h2> <p class="muted">Backend FastAPI : http://127.0.0.1:8000</p> <p class="muted">Frontend : http://127.0.0.1:5173</p> <p class="muted">GPU : désactivé pour l’assistant local</p></div></div></section>`);
}
//#endregion
export { _page as default };
