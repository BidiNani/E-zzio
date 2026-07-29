import { G as attr, c as ensure_array_like, l as head, q as escape_html } from "../../../chunks/dev.js";
//#region src/routes/living/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		const api = "http://127.0.0.1:8000/api/v23/living";
		let status = null;
		let quality = null;
		let hippo = null;
		let journal = null;
		let routeText = "Prépare une évolution constructive et professionnelle de BrotherEye CPU-only";
		let memoryText = "V23.10 installe Hippocampe PRO, Quality Gate et Journal d'Évolution.";
		let searchText = "Hippocampe Quality Gate";
		let error = "";
		let busy = false;
		async function getJson(url, options = {}) {
			const response = await fetch(url, options);
			const data = await response.json();
			if (!response.ok) throw new Error(JSON.stringify(data));
			return data;
		}
		async function refresh() {
			error = "";
			try {
				status = await getJson(`${api}/status`);
				quality = await getJson(`${api}/quality/gate`);
				hippo = await getJson(`${api}/hippocampus/status`);
				journal = await getJson(`${api}/evolution/journal?limit=10`);
			} catch (e) {
				error = String(e);
			}
		}
		refresh();
		head("n8hc7m", $$renderer, ($$renderer) => {
			$$renderer.title(($$renderer) => {
				$$renderer.push(`<title>BrotherEye V23.10 Evolution</title>`);
			});
		});
		$$renderer.push(`<main class="page svelte-n8hc7m"><section class="hero svelte-n8hc7m"><p class="kicker svelte-n8hc7m">BrotherEye V23.10</p> <h1 class="svelte-n8hc7m">Hippocampe PRO + Quality Gate</h1> <p class="lead svelte-n8hc7m">Une évolution constructive : mémoire robuste, journal d'évolution, quality gate,
      snapshots et diagnostic professionnel. Toujours local, fluide et CPU-only.</p> <div class="pills svelte-n8hc7m"><span class="svelte-n8hc7m">GPU : ${escape_html(status?.gpu_policy || "...")}</span> <span class="svelte-n8hc7m">num_gpu : ${escape_html(status?.num_gpu ?? "...")}</span> <span class="svelte-n8hc7m">Quality : ${escape_html(quality?.ok ? "OK" : "À vérifier")}</span> <span class="svelte-n8hc7m">Short : ${escape_html(hippo?.stats?.short_count ?? 0)}</span> <span class="svelte-n8hc7m">Long : ${escape_html(hippo?.stats?.long_count ?? 0)}</span> <span class="svelte-n8hc7m">Events : ${escape_html(hippo?.stats?.event_count ?? 0)}</span></div> <nav class="links svelte-n8hc7m"><a href="/band" class="svelte-n8hc7m">/band</a> <a href="/council" class="svelte-n8hc7m">/council</a> <a href="/senses" class="svelte-n8hc7m">/senses legacy</a> <a href="/friend" class="svelte-n8hc7m">/friend legacy</a> <a href="/quality" class="svelte-n8hc7m">/quality</a></nav></section> `);
		if (error) {
			$$renderer.push("<!--[0-->");
			$$renderer.push(`<section class="card danger svelte-n8hc7m"><h2>Erreur</h2> <pre class="svelte-n8hc7m">${escape_html(error)}</pre></section>`);
		} else $$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> <section class="grid three svelte-n8hc7m"><article class="card svelte-n8hc7m"><h2>Status</h2> <p><strong>Version :</strong> ${escape_html(status?.version || "...")}</p> <p><strong>Identité :</strong> ${escape_html(status?.identity?.metaphor || "Ami Vice Versa professionnel")}</p> <button${attr("disabled", busy, true)} class="svelte-n8hc7m">Rafraîchir</button></article> <article class="card svelte-n8hc7m"><h2>Quality Gate</h2> <p><strong>OK :</strong> ${escape_html(quality?.ok ? "oui" : "non")}</p> <p><strong>Erreurs :</strong> ${escape_html(quality?.errors?.length ?? 0)}</p> <p><strong>Warnings :</strong> ${escape_html(quality?.warnings?.length ?? 0)}</p> <button${attr("disabled", busy, true)} class="svelte-n8hc7m">Snapshot évolution</button></article> <article class="card svelte-n8hc7m"><h2>Hippocampe</h2> <p><strong>DB :</strong> ${escape_html(hippo?.stats?.db_path || "...")}</p> <p><strong>Embeddings :</strong> ${escape_html(hippo?.stats?.embedding_model || "nomic-embed-text")}</p> <p><strong>État :</strong> ${escape_html(hippo?.stats?.embedding_status || "...")}</p></article></section> <section class="card svelte-n8hc7m"><h2>Router organique</h2> <textarea class="svelte-n8hc7m">`);
		const $$body = escape_html(routeText);
		if ($$body) $$renderer.push(`${$$body}`);
		$$renderer.push(`</textarea> <button${attr("disabled", busy, true)} class="svelte-n8hc7m">Router + mémoriser</button> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></section> <section class="grid two svelte-n8hc7m"><article class="card svelte-n8hc7m"><h2>Mémoire longue</h2> <textarea class="svelte-n8hc7m">`);
		const $$body_1 = escape_html(memoryText);
		if ($$body_1) $$renderer.push(`${$$body_1}`);
		$$renderer.push(`</textarea> <button${attr("disabled", busy, true)} class="svelte-n8hc7m">Mémoriser PRO</button> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></article> <article class="card svelte-n8hc7m"><h2>Recherche mémoire</h2> <textarea class="svelte-n8hc7m">`);
		const $$body_2 = escape_html(searchText);
		if ($$body_2) $$renderer.push(`${$$body_2}`);
		$$renderer.push(`</textarea> <button${attr("disabled", busy, true)} class="svelte-n8hc7m">Chercher</button> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></article></section> <section class="card svelte-n8hc7m"><h2>Journal d'évolution</h2> `);
		if (journal?.journal) {
			$$renderer.push("<!--[0-->");
			$$renderer.push(`<pre class="svelte-n8hc7m">${escape_html(JSON.stringify(journal.journal, null, 2))}</pre>`);
		} else {
			$$renderer.push("<!--[-1-->");
			$$renderer.push(`<p>Aucun événement chargé.</p>`);
		}
		$$renderer.push(`<!--]--></section> <section class="card svelte-n8hc7m"><h2>Sens, talents, compétences</h2> `);
		if (status?.organs) {
			$$renderer.push("<!--[0-->");
			$$renderer.push(`<div class="organs svelte-n8hc7m"><!--[-->`);
			const each_array = ensure_array_like(Object.entries(status.organs));
			for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
				let [key, organ] = each_array[$$index];
				$$renderer.push(`<article class="organ svelte-n8hc7m"><p class="organ-key svelte-n8hc7m">${escape_html(key)}</p> <h3>${escape_html(organ.label)}</h3> <p><strong>Sens :</strong> ${escape_html(organ.sense)}</p> <p><strong>Talent :</strong> ${escape_html(organ.talent)}</p> <p><strong>Compétence :</strong> ${escape_html(organ.competence)}</p> <p><strong>Émotion :</strong> ${escape_html(organ.emotion)}</p> <p><strong>Actif :</strong> ${escape_html(organ.active_model)}</p> <p><strong>Statut :</strong> ${escape_html(organ.status)}</p></article>`);
			}
			$$renderer.push(`<!--]--></div>`);
		} else $$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></section></main>`);
	});
}
//#endregion
export { _page as default };
