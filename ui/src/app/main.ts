import { mount } from "svelte";

import { CoreClient } from "../core";
import App from "./App.svelte";

const target = document.getElementById("app");
if (target === null) {
  throw new Error("В index.html нет элемента #app — точки монтирования приложения");
}

const client = new CoreClient({ url: import.meta.env.VITE_CORE_URL });
client.start();

export default mount(App, { target, props: { client } });
