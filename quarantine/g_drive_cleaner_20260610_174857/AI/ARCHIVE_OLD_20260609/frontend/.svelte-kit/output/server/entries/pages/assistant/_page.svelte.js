import { G as attr, c as ensure_array_like, l as head, n as attr_class, q as escape_html } from "../../../chunks/dev.js";
//#region src/routes/assistant/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		const apiBase = "http://127.0.0.1:8000";
		let draft = "bonjour, quel temps fait-il à marseille ?";
		let mode = "auto";
		let notice = "";
		let history = [];
		let context = {
			mode: "auto",
			backend: "FastAPI",
			tools: "V23 organique",
			gpu: "Désactivé",
			panel: "Sens · talents · compétences"
		};
		async function getJson(url, options = {}) {
			const response = await fetch(url, options);
			const data = await response.json();
			if (!response.ok) throw new Error(JSON.stringify(data));
			return data;
		}
		async function refreshStatus() {
			try {
				context.gpu = (await getJson(`${apiBase}/api/v23/living/status`))?.gpu_policy === "disabled_for_brothereye" ? "Désactivé" : "À vérifier";
				context.backend = "FastAPI";
				context.tools = "V23 organique";
				context.mode = "auto";
				notice = "Interface alignée sur /api/chat et cœur organique V23.";
			} catch (e) {
				notice = "Interface prête, backend à vérifier.";
			}
		}
		refreshStatus();
		head("12tm3zb", $$renderer, ($$renderer) => {
			$$renderer.title(($$renderer) => {
				$$renderer.push(`<title>BrotherEye Assistant</title>`);
			});
		});
		$$renderer.push(`<main class="page svelte-12tm3zb"><section class="header svelte-12tm3zb"><p class="section-label svelte-12tm3zb">Assistant</p> <h1 class="svelte-12tm3zb">Conversation</h1> <p class="svelte-12tm3zb">Écris naturellement. L’assistant route vers les sens, talents et compétences du cœur V23.</p></section> <div class="layout svelte-12tm3zb"><section class="panel svelte-12tm3zb"><div class="panel-head svelte-12tm3zb"><h2 class="svelte-12tm3zb">Nouvelle demande</h2> `);
		$$renderer.select({
			value: mode,
			class: ""
		}, ($$renderer) => {
			$$renderer.option({ value: "auto" }, ($$renderer) => {
				$$renderer.push(`Automatique`);
			});
			$$renderer.option({ value: "presence" }, ($$renderer) => {
				$$renderer.push(`Présence`);
			});
			$$renderer.option({ value: "mains" }, ($$renderer) => {
				$$renderer.push(`Mains · code`);
			});
			$$renderer.option({ value: "intuition" }, ($$renderer) => {
				$$renderer.push(`Intuition`);
			});
			$$renderer.option({ value: "regard_critique" }, ($$renderer) => {
				$$renderer.push(`Regard critique`);
			});
			$$renderer.option({ value: "voix_premium" }, ($$renderer) => {
				$$renderer.push(`Voix premium`);
			});
			$$renderer.option({ value: "hippocampe" }, ($$renderer) => {
				$$renderer.push(`Hippocampe`);
			});
			$$renderer.option({ value: "oreille_musicale" }, ($$renderer) => {
				$$renderer.push(`Oreille musicale`);
			});
		}, "svelte-12tm3zb");
		$$renderer.push(`</div> <textarea placeholder="Écris ta demande..." class="svelte-12tm3zb">`);
		const $$body = escape_html(draft);
		if ($$body) $$renderer.push(`${$$body}`);
		$$renderer.push(`</textarea> <div class="actions svelte-12tm3zb"><span>Ctrl + Entrée pour envoyer.</span> <button${attr("disabled", !draft.trim(), true)} class="svelte-12tm3zb">${escape_html("Envoyer")}</button></div> `);
		if (notice) {
			$$renderer.push("<!--[0-->");
			$$renderer.push(`<div class="notice ok svelte-12tm3zb">${escape_html(notice)}</div>`);
		} else $$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--> <section class="history svelte-12tm3zb">`);
		if (history.length === 0) {
			$$renderer.push("<!--[0-->");
			$$renderer.push(`<div class="empty svelte-12tm3zb">L’historique local apparaîtra ici. Rien n’est encombré tant que tu n’as pas commencé.</div>`);
		} else {
			$$renderer.push("<!--[-1-->");
			$$renderer.push(`<!--[-->`);
			const each_array = ensure_array_like(history);
			for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
				let item = each_array[$$index];
				$$renderer.push(`<article${attr_class("bubble " + item.role, "svelte-12tm3zb")}><p class="svelte-12tm3zb">${escape_html(item.content)}</p> `);
				if (item.meta) {
					$$renderer.push("<!--[0-->");
					$$renderer.push(`<small class="svelte-12tm3zb">${escape_html(item.meta.organ || "Organe auto")} · ${escape_html(item.meta.model || "modèle auto")} · GPU ${escape_html(item.meta.gpu_policy || "disabled")}</small>`);
				} else $$renderer.push("<!--[-1-->");
				$$renderer.push(`<!--]--></article>`);
			}
			$$renderer.push(`<!--]-->`);
		}
		$$renderer.push(`<!--]--></section></section> <aside class="context svelte-12tm3zb"><h2 class="svelte-12tm3zb">Contexte</h2> <p class="svelte-12tm3zb">Les détails sont visibles mais restent secondaires.</p> <div class="row svelte-12tm3zb"><span class="svelte-12tm3zb">Mode</span><strong>${escape_html(context.mode)}</strong></div> <div class="row svelte-12tm3zb"><span class="svelte-12tm3zb">Backend</span><strong>${escape_html(context.backend)}</strong></div> <div class="row svelte-12tm3zb"><span class="svelte-12tm3zb">Outils</span><strong>${escape_html(context.tools)}</strong></div> <div class="row svelte-12tm3zb"><span class="svelte-12tm3zb">GPU</span><strong>${escape_html(context.gpu)}</strong></div> <div class="row svelte-12tm3zb"><span class="svelte-12tm3zb">Panel</span><strong>${escape_html(context.panel)}</strong></div></aside></div> <div class="floating svelte-12tm3zb"><span class="dot svelte-12tm3zb"></span> BrotherEye V23 · organique · CPU-only</div></main>`);
	});
}
//#endregion
export { _page as default };
