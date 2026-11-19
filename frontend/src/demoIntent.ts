// One-shot hand-off from the landing's "Run the 60-second demo" to the engine runtime console.
let requested = false;
export const requestDemo = () => { requested = true; };
export const consumeDemoRequest = () => { const was = requested; requested = false; return was; };
