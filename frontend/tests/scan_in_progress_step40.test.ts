import {
  describe,
  expect,
  it
} from "vitest";

import {
  ApiError
} from "../src/lib/api";
import {
  classifyScanError
} from "../src/lib/scanErrors";

describe(
  "serialized scan UX",
  () => {
    it(
      "maps backend scan_in_progress",
      () => {
        const view =
          classifyScanError(
            new ApiError(
              409,
              {
                detail: {
                  code:
                    "scan_in_progress"
                }
              }
            )
          );

        expect(
          view.kind
        ).toBe(
          "scan_in_progress"
        );

        expect(
          view.title
        ).toContain(
          "andamento"
        );
      }
    );
  }
);
