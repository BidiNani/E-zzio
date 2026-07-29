import "../../../chunks/index-server.js";
import { n as attr_class, q as escape_html } from "../../../chunks/dev.js";
import "../../../chunks/status.js";
//#region src/routes/quality/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let gpuOk;
		let hardware = null;
		$: gpuOk = false;
		$$renderer.push(`<section class="page"><div class="page-header"><div><p class="eyebrow">Qualité</p> <h1>Système &amp; vérification</h1> <p class="lead">Une vue claire pour savoir si le système est fiable, sans afficher les logs bruts au premier niveau.</p></div> <span${attr_class("badge", void 0, {
			"success": hardware,
			"warning": false
		})}><span${attr_class("dot", void 0, {
			"success": hardware,
			"warning": false
		})}></span> ${escape_html("Chargement")}</span></div> <div class="grid grid-4"><div class="card metric"><span class="metric-label">Backend</span> <span class="metric-value">${escape_html("—")}</span> <span class="small muted">FastAPI</span></div> <div class="card metric"><span class="metric-label">GPU policy</span> <span class="metric-value">${escape_html(gpuOk ? "OK" : "À vérifier")}</span> <span class="small muted">${escape_html("—")} / num_gpu=${escape_html("—")}</span></div> <div class="card metric"><span class="metric-label">Health endpoint</span> <span class="metric-value">${escape_html("Fallback")}</span> <span class="small muted">${escape_html("/api/hardware/status")}</span></div> <div class="card metric"><span class="metric-label">Snapshot</span> <span class="metric-value">À relier</span> <span class="small muted">Rapports locaux</span></div></div> <div class="card"><h2>Détails lisibles</h2> <div class="stack"><div class="info-row svelte-5zwhru"><span class="svelte-5zwhru">CPU</span> <strong>${escape_html("—")}</strong></div> <div class="info-row svelte-5zwhru"><span class="svelte-5zwhru">GPU utilisé par l’assistant</span> <strong>${escape_html(gpuOk ? "Non" : "À vérifier")}</strong></div> <div class="info-row svelte-5zwhru"><span class="svelte-5zwhru">Source health</span> <strong>${escape_html("fallback local")}</strong></div></div></div></section>`);
	});
}
//#endregion
export { _page as default };
