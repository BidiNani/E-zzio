import "../../../chunks/index-server.js";
import { G as attr, l as head, q as escape_html } from "../../../chunks/dev.js";
//#region src/routes/band/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let loading = false;
		let title = "brothereye_riot";
		let style = "grunge";
		let mood = "angry";
		let key = "E";
		let bpm = 142;
		let bars = 32;
		let intensity = .82;
		let palmMute = true;
		let doubleKick = false;
		head("37ag98", $$renderer, ($$renderer) => {
			$$renderer.title(($$renderer) => {
				$$renderer.push(`<title>BrotherEye AI Band Studio</title>`);
			});
		});
		$$renderer.push(`<main class="page svelte-37ag98"><section class="hero svelte-37ag98"><p class="eyebrow svelte-37ag98">BrotherEye V22.7</p> <h1 class="svelte-37ag98">AI Band Studio</h1> <p class="subtitle svelte-37ag98">Génération MAO locale rock, grunge, punk et métal : batterie, basse, guitares,
      lead, full mix, stems WAV et MIDI exportable dans ton DAW.</p></section> <section class="panel presets svelte-37ag98"><button class="svelte-37ag98">Rock</button> <button class="svelte-37ag98">Grunge</button> <button class="svelte-37ag98">Punk</button> <button class="svelte-37ag98">Metal</button> <button class="svelte-37ag98">Doom</button> <button class="svelte-37ag98">Hardcore</button></section> <section class="panel svelte-37ag98"><h2>Composer un morceau</h2> <div class="grid-form svelte-37ag98"><label class="svelte-37ag98">Titre<input${attr("value", title)} class="svelte-37ag98"/></label> <label class="svelte-37ag98">Style `);
		$$renderer.select({
			value: style,
			class: ""
		}, ($$renderer) => {
			$$renderer.option({ value: "rock" }, ($$renderer) => {
				$$renderer.push(`Rock`);
			});
			$$renderer.option({ value: "grunge" }, ($$renderer) => {
				$$renderer.push(`Grunge`);
			});
			$$renderer.option({ value: "punk" }, ($$renderer) => {
				$$renderer.push(`Punk`);
			});
			$$renderer.option({ value: "metal" }, ($$renderer) => {
				$$renderer.push(`Metal`);
			});
			$$renderer.option({ value: "doom" }, ($$renderer) => {
				$$renderer.push(`Doom`);
			});
			$$renderer.option({ value: "hardcore" }, ($$renderer) => {
				$$renderer.push(`Hardcore`);
			});
		}, "svelte-37ag98");
		$$renderer.push(`</label> <label class="svelte-37ag98">Humeur<input${attr("value", mood)} class="svelte-37ag98"/></label> <label class="svelte-37ag98">Tonalité<input${attr("value", key)} class="svelte-37ag98"/></label> <label class="svelte-37ag98">BPM<input type="number"${attr("value", bpm)} min="55" max="220" class="svelte-37ag98"/></label> <label class="svelte-37ag98">Mesures<input type="number"${attr("value", bars)} min="4" max="96" class="svelte-37ag98"/></label> <label class="svelte-37ag98">Intensité<input type="number" step="0.01"${attr("value", intensity)} min="0.1" max="1" class="svelte-37ag98"/></label> <label class="check svelte-37ag98"><input type="checkbox"${attr("checked", palmMute, true)} class="svelte-37ag98"/> Palm mute</label> <label class="check svelte-37ag98"><input type="checkbox"${attr("checked", doubleKick, true)} class="svelte-37ag98"/> Double kick</label></div> <button class="main svelte-37ag98"${attr("disabled", loading, true)}>${escape_html("Générer le groupe")}</button></section> `);
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
