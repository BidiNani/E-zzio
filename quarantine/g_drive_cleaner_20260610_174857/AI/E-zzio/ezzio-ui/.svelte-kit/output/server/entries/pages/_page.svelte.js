import "../../chunks/index-server.js";
import { L as attr, R as clsx, a as ensure_array_like, n as attr_class, o as head, r as attr_style, z as escape_html } from "../../chunks/dev.js";
function pretty(value) {
	return JSON.stringify(value ?? {}, null, 2);
}
function safeValue(value) {
	if (value === void 0 || value === null || value === "") return "—";
	if (typeof value === "object") return JSON.stringify(value);
	return value;
}
function shortText(value, max = 180) {
	const text = String(value ?? "—");
	if (text.length <= max) return text;
	return text.slice(0, max - 1) + "…";
}
//#endregion
//#region src/routes/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let root = null;
		let maintenance = null;
		let safeActions = null;
		let cloud = null;
		let human = null;
		let supervisor = null;
		let performance = null;
		let forge = null;
		let vision = null;
		let activePanel = "timeline";
		let commanderText = "E-ZZIO, fais un état rapide de ton système.";
		let commanderOutput = {
			ok: true,
			reply: "Prêt."
		};
		let busy = false;
		let lastRefresh = "—";
		const panels = [
			["timeline", "Timeline"],
			["journal", "Journal"],
			["modules", "Modules"],
			["ledger", "Ledger"],
			["routers", "Routeurs"],
			["raw", "Raw"]
		];
		function valueOf(obj, path, fallback = "—") {
			try {
				return safeValue(path.split(".").reduce((acc, key) => acc?.[key], obj) ?? fallback);
			} catch {
				return fallback;
			}
		}
		function okish(obj) {
			return obj?.ok === true || obj?.online === true;
		}
		function badgeClass(value) {
			if (value === true || value === 0 || value === "ok") return "badge ok";
			if (value === false || value === null || value === void 0) return "badge warn";
			return "badge";
		}
		function moduleState(obj) {
			if (okish(obj)) return "OK";
			if (obj?.online === false) return "OFF";
			return "—";
		}
		function moduleBadge(obj) {
			if (okish(obj)) return "badge ok";
			if (obj?.online === false) return "badge warn";
			return "badge";
		}
		function livingMood() {
			let score = 100;
			const warnings = [];
			if (!okish(root)) {
				score -= 25;
				warnings.push("API incertaine");
			}
			score = Math.max(0, Math.min(100, score));
			let label = "Calme et opérationnel";
			if (score < 85) label = "Attentif";
			if (score < 65) label = "À surveiller";
			if (score < 45) label = "Besoin de maintenance";
			return {
				score,
				label,
				warnings: warnings.length ? warnings : ["Aucun signal critique"],
				focus: "assistance PC"
			};
		}
		function timelineItems() {
			const items = [];
			for (const q of []) items.push({
				kind: q.executed ? "executed" : q.cancelled ? "cancelled" : "pending",
				title: q.action_id || q.action || "safe-action",
				at: q.executed_at || q.cancelled_at || q.created_at || "—",
				text: q.summary || q.reason || q.description || q.proposal_id || "—"
			});
			for (const e of []) items.push({
				kind: "journal",
				title: e.type || e.event || "journal",
				at: e.created_at || e.at || "—",
				text: e.summary || e.note || e.text || JSON.stringify(e).slice(0, 240)
			});
			return items.filter(Boolean).sort((a, b) => String(b.at).localeCompare(String(a.at))).slice(0, 18);
		}
		function modules() {
			return [
				[
					"Backend",
					root,
					valueOf(root, "version")
				],
				[
					"Maintenance",
					maintenance,
					`bad=${valueOf(maintenance, "bad_count")}`
				],
				[
					"Safe Actions",
					safeActions,
					`pending=${valueOf(safeActions, "pending_count")}`
				],
				[
					"Human Loop",
					human,
					valueOf(human, "version")
				],
				[
					"Supervisor",
					supervisor,
					valueOf(supervisor, "version")
				],
				[
					"Performance",
					performance,
					valueOf(performance, "version")
				],
				[
					"Cloud Brain",
					cloud,
					`allow=${valueOf(cloud, "allow_send")}`
				],
				[
					"Forge",
					forge,
					valueOf(forge, "version")
				],
				[
					"Vision",
					vision,
					valueOf(vision, "model")
				]
			];
		}
		head("1uha8ag", $$renderer, ($$renderer) => {
			$$renderer.title(($$renderer) => {
				$$renderer.push(`<title>E-ZZIO — Living Cockpit</title>`);
			});
		});
		$$renderer.push(`<header class="topbar"><div class="topbar-inner"><div class="brand"><div class="orb"></div> <div><h1>E-ZZIO Living Cockpit</h1> <p>Ami IA local d’Enrik — vivant, prudent, utile, sans pub, CPU/RAM only.</p></div></div> <div class="badges"><span${attr_class(clsx(badgeClass(void 0)))}>API ${escape_html("—")}</span> <span class="badge ok">GPU untouched</span> <span class="badge ok">No ads</span> <span${attr_class(clsx("badge ok"))}>pending ${escape_html(valueOf(safeActions, "pending_count"))}</span> <span class="badge">refresh ${escape_html(lastRefresh)}</span></div></div></header> <main class="container"><div class="grid"><section class="card glow span-4"><div class="card-head"><div><h2>État vivant</h2> <div class="hint">Synthèse locale de santé et priorité</div></div> <span${attr_class(clsx(livingMood().score >= 85 ? "badge ok" : livingMood().score >= 65 ? "badge warn" : "badge bad"))}>${escape_html(livingMood().score)}%</span></div> <div class="card-body mood"><div class="kv"><div class="kv-row"><span class="key">Humeur</span><span class="value">${escape_html(livingMood().label)}</span></div> <div class="kv-row"><span class="key">Focus</span><span class="value">${escape_html(livingMood().focus)}</span></div> <div class="kv-row"><span class="key">Signaux</span><span class="value">${escape_html(livingMood().warnings.join(" · "))}</span></div></div> <div class="mood-line"><div class="mood-fill"${attr_style(`--w:${livingMood().score}%`)}></div></div></div></section> <section class="card span-2"><div class="card-head"><div><h2>Maintenance</h2> <div class="hint">Audit</div></div></div> <div class="card-body kv"><div class="kv-row"><span class="key">OK</span><span class="value">${escape_html(valueOf(maintenance, "ok"))}</span></div> <div class="kv-row"><span class="key">Bad</span><span class="value">${escape_html(valueOf(maintenance, "bad_count"))}</span></div> <div class="kv-row"><span class="key">Dust</span><span class="value">${escape_html(valueOf(maintenance, "dust_candidate_count"))}</span></div></div></section> <section class="card span-2"><div class="card-head"><div><h2>Actions</h2> <div class="hint">Ledger</div></div></div> <div class="card-body kv"><div class="kv-row"><span class="key">Queued</span><span class="value">${escape_html(valueOf(safeActions, "queued_count"))}</span></div> <div class="kv-row"><span class="key">Done</span><span class="value">${escape_html(valueOf(safeActions, "executed_count"))}</span></div> <div class="kv-row"><span class="key">Pending</span><span class="value">${escape_html(valueOf(safeActions, "pending_count"))}</span></div></div></section> <section class="card span-2"><div class="card-head"><div><h2>Cloud</h2> <div class="hint">Optionnel</div></div></div> <div class="card-body kv"><div class="kv-row"><span class="key">OK</span><span class="value">${escape_html(valueOf(cloud, "ok"))}</span></div> <div class="kv-row"><span class="key">Send</span><span class="value">${escape_html(valueOf(cloud, "allow_send"))}</span></div> <div class="kv-row"><span class="key">Usage</span><span class="value">${escape_html(valueOf(cloud, "usage.total_today"))}</span></div></div></section> <section class="card span-2"><div class="card-head"><div><h2>Vision/Forge</h2> <div class="hint">Créatif</div></div></div> <div class="card-body kv"><div class="kv-row"><span class="key">Vision</span><span class="value">${escape_html(moduleState(vision))}</span></div> <div class="kv-row"><span class="key">Forge</span><span class="value">${escape_html(moduleState(forge))}</span></div> <div class="kv-row"><span class="key">Comfy</span><span class="value">${escape_html(valueOf(forge, "comfyui_online"))}</span></div></div></section> <section class="card span-7"><div class="card-head"><div><h2>Commander</h2> <div class="hint">Dialogue central → proposition → confirmation → exécution sûre</div></div> <span${attr_class(clsx("badge ok"))}>${escape_html("Prêt")}</span></div> <div class="card-body"><textarea>`);
		const $$body = escape_html(commanderText);
		if ($$body) $$renderer.push(`${$$body}`);
		$$renderer.push(`</textarea> <div class="actions"><button class="primary"${attr("disabled", busy, true)}>Envoyer</button> <button${attr("disabled", busy, true)}>État</button> <button${attr("disabled", busy, true)}>Audit</button> <button${attr("disabled", busy, true)}>Optimisation sûre</button> <button${attr("disabled", busy, true)}>Journal</button> <button class="primary"${attr("disabled", busy, true)}>CONFIRME</button> <button class="danger"${attr("disabled", busy, true)}>Annule</button></div> <div class="reply"><pre>${escape_html(pretty(commanderOutput))}</pre></div></div></section> <section class="card span-5"><div class="card-head"><div><h2>Modules</h2> <div class="hint">Présence des organes E-ZZIO</div></div></div> <div class="card-body"><div class="module-grid"><!--[-->`);
		const each_array = ensure_array_like(modules());
		for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
			let mod = each_array[$$index];
			$$renderer.push(`<div class="module"><div class="item-title"><span class="module-name">${escape_html(mod[0])}</span> <span${attr_class(clsx(moduleBadge(mod[1])))}>${escape_html(moduleState(mod[1]))}</span></div> <div class="module-detail">${escape_html(shortText(mod[2], 80))}</div></div>`);
		}
		$$renderer.push(`<!--]--></div></div></section> <section class="card span-12"><div class="card-head"><div><h2>Observatoire vivant</h2> <div class="hint">Timeline, journal, modules, ledger et routeurs</div></div> <div class="tabs"><!--[-->`);
		const each_array_1 = ensure_array_like(panels);
		for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
			let panel = each_array_1[$$index_1];
			$$renderer.push(`<button${attr_class("tab", void 0, { "active": activePanel === panel[0] })}>${escape_html(panel[1])}</button>`);
		}
		$$renderer.push(`<!--]--> <button class="tab">Rafraîchir</button> <button class="tab">Auto ${escape_html("ON")}</button></div></div> <div class="card-body">`);
		{
			$$renderer.push("<!--[0-->");
			$$renderer.push(`<div class="timeline"><!--[-->`);
			const each_array_2 = ensure_array_like(timelineItems());
			for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
				let item = each_array_2[$$index_2];
				$$renderer.push(`<div class="timeline-item"><div class="timeline-top"><span>${escape_html(item.title)}</span> <span${attr_class(clsx(item.kind === "executed" ? "badge ok" : item.kind === "cancelled" ? "badge bad" : "badge warn"))}>${escape_html(item.kind)}</span></div> <div class="timeline-text">${escape_html(item.at)}</div> <div class="timeline-text">${escape_html(shortText(item.text, 260))}</div></div>`);
			}
			$$renderer.push(`<!--]--></div>`);
		}
		$$renderer.push(`<!--]--></div></section></div></main>`);
	});
}
//#endregion
export { _page as default };
