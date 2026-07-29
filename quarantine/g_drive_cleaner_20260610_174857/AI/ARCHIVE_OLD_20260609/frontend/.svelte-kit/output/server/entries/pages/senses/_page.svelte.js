import "../../../chunks/index-server.js";
import { G as attr, l as head, q as escape_html } from "../../../chunks/dev.js";
//#region src/routes/senses/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let message = "J’ai besoin d’un conseil stratégique et humain pour mon projet.";
		let mode = "auto";
		let allowDeep = false;
		let premiumConfirmed = false;
		head("om0bj8", $$renderer, ($$renderer) => {
			$$renderer.title(($$renderer) => {
				$$renderer.push(`<title>BrotherEye Model Senses</title>`);
			});
		});
		$$renderer.push(`<main class="page svelte-om0bj8"><section class="hero svelte-om0bj8"><p class="eyebrow svelte-om0bj8">BrotherEye V22.5</p> <h1 class="svelte-om0bj8">Model Senses</h1> <p class="subtitle svelte-om0bj8">Chaque modèle devient un sens, un talent et une émotion. BrotherEye ne choisit plus seulement
      un moteur : il active une partie de son système intérieur.</p></section> <section class="panel svelte-om0bj8"><h2>Tester l’activation d’un sens</h2> <textarea rows="5" placeholder="Écris une demande..." class="svelte-om0bj8">`);
		const $$body = escape_html(message);
		if ($$body) $$renderer.push(`${$$body}`);
		$$renderer.push(`</textarea> <div class="controls svelte-om0bj8"><label class="svelte-om0bj8">Mode `);
		$$renderer.select({
			value: mode,
			class: ""
		}, ($$renderer) => {
			$$renderer.option({ value: "auto" }, ($$renderer) => {
				$$renderer.push(`Auto`);
			});
			$$renderer.option({ value: "friend" }, ($$renderer) => {
				$$renderer.push(`Présence rapide`);
			});
			$$renderer.option({ value: "friend_plus" }, ($$renderer) => {
				$$renderer.push(`Intuition sociale`);
			});
			$$renderer.option({ value: "natural_friend" }, ($$renderer) => {
				$$renderer.push(`Voix naturelle`);
			});
			$$renderer.option({ value: "code" }, ($$renderer) => {
				$$renderer.push(`Mains / code`);
			});
			$$renderer.option({ value: "vision" }, ($$renderer) => {
				$$renderer.push(`Yeux / vision`);
			});
			$$renderer.option({ value: "reason" }, ($$renderer) => {
				$$renderer.push(`Pensée profonde`);
			});
			$$renderer.option({ value: "deep_quality" }, ($$renderer) => {
				$$renderer.push(`Regard critique`);
			});
			$$renderer.option({ value: "premium_smart" }, ($$renderer) => {
				$$renderer.push(`Voix premium`);
			});
			$$renderer.option({ value: "premium_slow" }, ($$renderer) => {
				$$renderer.push(`Grande voix lente`);
			});
		}, "svelte-om0bj8");
		$$renderer.push(`</label> <label class="check svelte-om0bj8"><input type="checkbox"${attr("checked", allowDeep, true)}/> Autoriser profond</label> <label class="check svelte-om0bj8"><input type="checkbox"${attr("checked", premiumConfirmed, true)}/> Confirmer premium</label> <button${attr("disabled", !message.trim(), true)} class="svelte-om0bj8">${escape_html("Activer")}</button></div></section> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> `);
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
