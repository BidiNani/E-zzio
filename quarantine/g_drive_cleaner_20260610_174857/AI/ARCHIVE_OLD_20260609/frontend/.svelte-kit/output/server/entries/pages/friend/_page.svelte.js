import { G as attr, c as ensure_array_like, l as head, q as escape_html } from "../../../chunks/dev.js";
//#region src/routes/friend/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let message = "";
		let allowDeep = false;
		let premiumConfirmed = false;
		let mode = "auto";
		const examples = [
			"Réponds comme un ami intelligent et aide-moi à prioriser.",
			"Corrige ce script PowerShell proprement.",
			"Analyse profondément la stratégie du projet.",
			"Fais une réponse premium plus qualitative.",
			"Je veux une réponse naturelle, presque comme un compagnon."
		];
		head("gw78nt", $$renderer, ($$renderer) => {
			$$renderer.title(($$renderer) => {
				$$renderer.push(`<title>BrotherEye Smart Router</title>`);
			});
		});
		$$renderer.push(`<main class="friend-page svelte-gw78nt"><section class="hero svelte-gw78nt"><p class="eyebrow svelte-gw78nt">BrotherEye V22.4</p> <h1 class="svelte-gw78nt">Smart Model Router</h1> <p class="subtitle svelte-gw78nt">BrotherEye choisit le bon modèle selon la demande : vitesse, ami intelligent,
      code, vision, raisonnement profond ou premium confirmé.</p></section> <section class="panel controls svelte-gw78nt"><label class="svelte-gw78nt">Mode `);
		$$renderer.select({
			value: mode,
			class: ""
		}, ($$renderer) => {
			$$renderer.option({ value: "auto" }, ($$renderer) => {
				$$renderer.push(`Auto`);
			});
			$$renderer.option({ value: "fast" }, ($$renderer) => {
				$$renderer.push(`Rapide`);
			});
			$$renderer.option({ value: "friend" }, ($$renderer) => {
				$$renderer.push(`Ami rapide`);
			});
			$$renderer.option({ value: "friend_plus" }, ($$renderer) => {
				$$renderer.push(`Ami approfondi`);
			});
			$$renderer.option({ value: "natural_friend" }, ($$renderer) => {
				$$renderer.push(`Naturel / agentic`);
			});
			$$renderer.option({ value: "code" }, ($$renderer) => {
				$$renderer.push(`Code`);
			});
			$$renderer.option({ value: "vision" }, ($$renderer) => {
				$$renderer.push(`Vision`);
			});
			$$renderer.option({ value: "quality" }, ($$renderer) => {
				$$renderer.push(`Qualité`);
			});
			$$renderer.option({ value: "reason" }, ($$renderer) => {
				$$renderer.push(`Raisonnement profond`);
			});
			$$renderer.option({ value: "deep_quality" }, ($$renderer) => {
				$$renderer.push(`Audit profond`);
			});
			$$renderer.option({ value: "premium_smart" }, ($$renderer) => {
				$$renderer.push(`Premium smart`);
			});
			$$renderer.option({ value: "premium_slow" }, ($$renderer) => {
				$$renderer.push(`Premium lent`);
			});
		}, "svelte-gw78nt");
		$$renderer.push(`</label> <label class="check svelte-gw78nt"><input type="checkbox"${attr("checked", allowDeep, true)}/> Autoriser modèles profonds</label> <label class="check svelte-gw78nt"><input type="checkbox"${attr("checked", premiumConfirmed, true)}/> Confirmer premium</label></section> <section class="panel svelte-gw78nt"><textarea placeholder="Parle à BrotherEye. Il choisira le meilleur modèle..." rows="7" class="svelte-gw78nt">`);
		const $$body = escape_html(message);
		if ($$body) $$renderer.push(`${$$body}`);
		$$renderer.push(`</textarea> <div class="actions svelte-gw78nt"><button${attr("disabled", !message.trim(), true)} class="svelte-gw78nt">${escape_html("Envoyer")}</button> <button class="secondary svelte-gw78nt"${attr("disabled", !message.trim(), true)}>Tester le routage</button></div> <div class="examples svelte-gw78nt"><!--[-->`);
		const each_array = ensure_array_like(examples);
		for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
			let item = each_array[$$index];
			$$renderer.push(`<button class="chip svelte-gw78nt">${escape_html(item)}</button>`);
		}
		$$renderer.push(`<!--]--></div></section> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></main>`);
	});
}
//#endregion
export { _page as default };
