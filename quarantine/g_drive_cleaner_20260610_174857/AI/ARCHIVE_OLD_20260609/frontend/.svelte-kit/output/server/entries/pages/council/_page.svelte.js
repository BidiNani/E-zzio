import "../../../chunks/index-server.js";
import { G as attr, l as head, q as escape_html } from "../../../chunks/dev.js";
//#region src/routes/council/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let musicLoading = false;
		let message = "Je veux une musique calme pour BrotherEye, avec une émotion de confiance.";
		let allowDeep = false;
		let premiumConfirmed = false;
		let title = "brothereye_theme";
		let mood = "calm";
		let style = "ambient";
		let key = "C";
		let bpm = 92;
		let bars = 8;
		head("1xq6vdg", $$renderer, ($$renderer) => {
			$$renderer.title(($$renderer) => {
				$$renderer.push(`<title>BrotherEye Inner Council</title>`);
			});
		});
		$$renderer.push(`<main class="page svelte-1xq6vdg"><section class="hero svelte-1xq6vdg"><p class="eyebrow svelte-1xq6vdg">BrotherEye V22.6</p> <h1 class="svelte-1xq6vdg">Inner Council</h1> <p class="subtitle svelte-1xq6vdg">BrotherEye active ses sens : présence, intuition, mains, yeux, mémoire, conscience,
      logique, archiviste et maintenant oreille musicale.</p></section> <section class="panel svelte-1xq6vdg"><h2>Demander au conseil intérieur</h2> <textarea rows="5" placeholder="Écris une demande..." class="svelte-1xq6vdg">`);
		const $$body = escape_html(message);
		if ($$body) $$renderer.push(`${$$body}`);
		$$renderer.push(`</textarea> <div class="controls svelte-1xq6vdg"><label class="check svelte-1xq6vdg"><input type="checkbox"${attr("checked", allowDeep, true)} class="svelte-1xq6vdg"/> Autoriser profond</label> <label class="check svelte-1xq6vdg"><input type="checkbox"${attr("checked", premiumConfirmed, true)} class="svelte-1xq6vdg"/> Confirmer premium</label> <button${attr("disabled", !message.trim(), true)} class="svelte-1xq6vdg">${escape_html("Activer le bon sens")}</button></div></section> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> <section class="panel music svelte-1xq6vdg"><h2>Music Lab local</h2> <p class="muted svelte-1xq6vdg">Génère un fichier WAV + MIDI localement, sans cloud.</p> <div class="music-grid svelte-1xq6vdg"><label class="svelte-1xq6vdg">Titre<input${attr("value", title)} class="svelte-1xq6vdg"/></label> <label class="svelte-1xq6vdg">Humeur<input${attr("value", mood)} class="svelte-1xq6vdg"/></label> <label class="svelte-1xq6vdg">Style<input${attr("value", style)} class="svelte-1xq6vdg"/></label> <label class="svelte-1xq6vdg">Tonalité<input${attr("value", key)} class="svelte-1xq6vdg"/></label> <label class="svelte-1xq6vdg">BPM<input type="number"${attr("value", bpm)} min="50" max="180" class="svelte-1xq6vdg"/></label> <label class="svelte-1xq6vdg">Mesures<input type="number"${attr("value", bars)} min="2" max="24" class="svelte-1xq6vdg"/></label></div> <button${attr("disabled", musicLoading, true)} class="svelte-1xq6vdg">${escape_html("Composer WAV + MIDI")}</button> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></section> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></main>`);
	});
}
//#endregion
export { _page as default };
