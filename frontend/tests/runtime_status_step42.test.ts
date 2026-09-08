import { describe, expect, it } from "vitest";
import { backendLabel, modelLabel, scannerLabel, schedulerLabel } from "../src/lib/runtimeUi";

describe("global runtime status labels",()=>{
 it("does not claim scanner state while backend is disconnected",()=>{expect(scannerLabel("ready",false).label).toBe("Sem backend");});
 it("distinguishes location permission from generic scanner failure",()=>{expect(scannerLabel("location_access_denied",true).label).toContain("Permissão");expect(scannerLabel("error",true).label).toBe("Erro");});
 it("keeps not-ready model distinct from a negative security decision",()=>{expect(modelLabel("not_ready",true).label).toBe("Não pronto");});
 it("reports backend recovery states separately",()=>{expect(backendLabel("reconnecting").label).toBe("Reconectando");expect(backendLabel("disconnected").label).toBe("Desconectado");});
 it("does not claim scheduler availability outside Electron",()=>{expect(schedulerLabel(null,true,false).label).toBe("Somente Electron");});
});
