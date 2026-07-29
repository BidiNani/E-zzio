

export const index = 10;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/senses/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/10.s_1Z7Wzf.js","_app/immutable/chunks/CPCnt2Sw.js","_app/immutable/chunks/xihTtKlq.js","_app/immutable/chunks/BnyQJLgt.js"];
export const stylesheets = ["_app/immutable/assets/10.jJSTg1ZQ.css"];
export const fonts = [];
