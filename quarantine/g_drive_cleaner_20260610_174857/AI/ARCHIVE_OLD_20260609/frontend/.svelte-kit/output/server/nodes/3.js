

export const index = 3;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/assistant/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/3.CY7ugnWI.js","_app/immutable/chunks/CPCnt2Sw.js","_app/immutable/chunks/xihTtKlq.js","_app/immutable/chunks/BnyQJLgt.js"];
export const stylesheets = ["_app/immutable/assets/3.BY-njP2u.css"];
export const fonts = [];
