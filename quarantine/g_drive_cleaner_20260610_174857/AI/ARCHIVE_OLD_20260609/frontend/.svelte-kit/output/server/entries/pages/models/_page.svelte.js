import "../../../chunks/index-server.js";
import { c as ensure_array_like, n as attr_class, q as escape_html } from "../../../chunks/dev.js";
import "../../../chunks/status.js";
import "../../../chunks/models.js";
//#region src/routes/models/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let ready, missingRequired;
		let models = [];
		$: ready = models.filter((model) => model.installed).length;
		$: missingRequired = models.filter((model) => model.required && !model.installed).length;
		$$renderer.push(`<section class="page"><div class="page-header"><div><p class="eyebrow">Modèles</p> <h1>Rôles IA</h1> <p class="lead">L’interface affiche des rôles simples. Le routeur choisit le bon modèle selon l’intention.</p></div> <span${attr_class("badge", void 0, {
			"success": missingRequired === 0,
			"warning": missingRequired > 0
		})}><span${attr_class("dot", void 0, {
			"success": missingRequired === 0,
			"warning": missingRequired > 0
		})}></span> ${escape_html(ready)}/${escape_html(models.length || 7)} prêts</span></div> <div class="card"><div class="spread model-summary svelte-18pldtr"><div><h2>Configuration recommandée</h2> <p class="muted">Source détectée : ${escape_html("fallback local")}.
          ${escape_html(" Chargement...")}</p></div></div> <div class="stack"><!--[-->`);
		const each_array = ensure_array_like(models);
		for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
			let model = each_array[$$index];
			$$renderer.push(`<div class="model-row svelte-18pldtr"><div><strong>${escape_html(model.role)}</strong> <span class="svelte-18pldtr">${escape_html(model.description)}</span></div> <code class="svelte-18pldtr">${escape_html(model.name)}</code> <span${attr_class("badge svelte-18pldtr", void 0, {
				"success": model.installed,
				"warning": !model.installed && !model.required,
				"danger": !model.installed && model.required
			})}><span${attr_class("dot svelte-18pldtr", void 0, {
				"success": model.installed,
				"warning": !model.installed && !model.required,
				"danger": !model.installed && model.required
			})}></span> ${escape_html(model.status)}</span></div>`);
		}
		$$renderer.push(`<!--]--></div></div> <div class="card-flat"><h2>Décision retenue</h2> <p class="muted">Rapide par défaut, qualité uniquement si nécessaire. Gemma4:12b reste un modèle de review/synthèse, pas le modèle quotidien.</p></div></section>`);
	});
}
//#endregion
export { _page as default };
