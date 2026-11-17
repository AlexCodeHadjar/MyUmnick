// Подпакет «controller» спутника: контроллер и его части; импорт снаружи — только через этот файл (R-06).
export { CompanionController, type Feed } from "./controller";
export { tauriPorts, type Ports } from "./ports";
export type { MainState } from "./presence";
