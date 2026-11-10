import { mount, unmount } from "svelte";

import { CoreClient, locale } from "../core";
import {
  EditionPicker,
  editionById,
  launcher,
  needsPicker,
  pickRequested,
  type Edition,
  type LauncherState,
} from "../features/edition";
import App from "./App.svelte";

const target = document.getElementById("app");
if (target === null) {
  throw new Error("В index.html нет элемента #app — точки монтирования приложения");
}
const root = target;
const port = launcher();

/** Главное окно издания: язык выставлен до подключения — интерфейс не мигает другим языком. */
function openApp(edition: Edition): void {
  locale.set(edition.lang);
  const client = new CoreClient({ url: import.meta.env.VITE_CORE_URL });
  client.store.expectedEdition = edition.id;
  client.start();
  document.addEventListener("visibilitychange", () => {
    client.setWindowVisible(!document.hidden);
  });
  mount(App, { target: root, props: { client } });
}

async function start(): Promise<void> {
  const state = await port.load();
  // Предзапуск (STAGE_20, 2.2): ядро прошлого издания стартует, пока пользователь смотрит на плитки.
  const preload = port.startCore(state.last);
  if (!needsPicker(state, pickRequested(location.search))) {
    await preload;
    openApp(editionById(state.last));
    return;
  }
  const picker = mount(EditionPicker, {
    target: root,
    props: {
      initial: state,
      onpick: async (edition: Edition, next: LauncherState) => {
        await preload.catch(() => undefined);
        await port.startCore(edition.id);
        await port.save(next);
        await unmount(picker);
        history.replaceState(null, "", location.pathname);
        openApp(edition);
      },
    },
  });
}

void start();
