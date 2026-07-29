import "../../chunks/dev.js";
//#region src/routes/+layout.svelte
function _layout($$renderer, $$props) {
	let { children } = $$props;
	$$renderer.push(`<div class="shell">`);
	children($$renderer);
	$$renderer.push(`<!----></div>`);
}
//#endregion
export { _layout as default };
