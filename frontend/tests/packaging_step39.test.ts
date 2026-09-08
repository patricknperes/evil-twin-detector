// @vitest-environment jsdom

import {
  describe,
  expect,
  it
} from "vitest";

describe(
  "desktop packaging source contract",
  () => {
    it(
      "keeps the production renderer importable",
      async () => {
        const app = await import(
          "../src/App"
        );

        expect(
          app.default
        ).toBeTruthy();
      },
      60_000
    );
  }
);
