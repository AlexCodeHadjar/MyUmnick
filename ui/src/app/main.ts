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
function openApp(edition: Edition, background: boolean): void {
  locale.set(edition.lang);
  const client = new CoreClient({ url: import.meta.env.VITE_CORE_URL });
  client.store.expectedEdition = edition.id;
  // Позвали по имени — окно из трея открывается (ADR-0041).
  client.onCalled(() => {
    void port.reveal().catch(() => undefined);
  });
  client.start();
  // Окно в трее (фон или крестик) — скрытое: персонаж сам не заговаривает (S-15.1).
  if (background || document.hidden) client.setWindowVisible(false);
  port.onShown((shown) => {
    client.setWindowVisible(shown);
  });
  document.addEventListener("visibilitychange", () => {
    client.setWindowVisible(!document.hidden);
  });
  mount(App, { target: root, props: { client, background } });
}

async function start(): Promise<void> {
  const [state, background] = await Promise.all([port.load(), port.background()]);
  // Предзапуск (STAGE_20, 2.2): ядро прошлого издания стартует, пока пользователь смотрит на плитки.
  const preload = port.startCore(state.last);
  // В фоне выбирать некому: открывается прошлое издание.
  if (background || !needsPicker(state, pickRequested(location.search))) {
    await preload;
    openApp(editionById(state.last), background);
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
        openApp(edition, false);
      },
    },
  });
}

void start();
