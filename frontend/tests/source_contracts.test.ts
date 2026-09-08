import {
  describe,
  expect,
  it,
  vi
} from "vitest";

import {
  API_BASE,
  api
} from "../src/lib/api";

describe(
  "frontend foundation",
  () => {
    it(
      "uses the local FastAPI backend by default",
      () => {
        expect(
          API_BASE
        ).toBe(
          "http://127.0.0.1:8765"
        );
      }
    );

    it(
      "requests the dashboard trends endpoint",
      async () => {
        const fetchMock = vi.fn(
          async () => ({
            ok: true,
            status: 200,
            json: async () => ({
              requested_limit: 30,
              returned: 0,
              points: []
            })
          })
        );

        vi.stubGlobal(
          "fetch",
          fetchMock
        );

        await api.dashboardTrends();

        expect(
          fetchMock
        ).toHaveBeenCalledWith(
          "http://127.0.0.1:8765/dashboard/trends",
          expect.any(Object)
        );

        vi.unstubAllGlobals();
      }
    );
  }
);
