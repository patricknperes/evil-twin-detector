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
  "scan error UX contracts",
  () => {
    it(
      "maps Windows location permission denial",
      () => {
        const view = classifyScanError(
          new ApiError(
            403,
            {
              detail: {
                code: "location_access_denied",
                message: "denied",
                settings_uri: "ms-settings:privacy-location"
              }
            }
          )
        );

        expect(view.kind).toBe(
          "location_access_denied"
        );
        expect(view.settingsUri).toBe(
          "ms-settings:privacy-location"
        );
      }
    );

    it(
      "keeps unsupported platform distinct",
      () => {
        const view = classifyScanError(
          new ApiError(
            501,
            {
              detail: {
                code: "unsupported_platform",
                message: "Windows required"
              }
            }
          )
        );

        expect(view.kind).toBe(
          "unsupported_platform"
        );
      }
    );

    it(
      "keeps native wlanapi metadata",
      () => {
        const view = classifyScanError(
          new ApiError(
            502,
            {
              detail: {
                code: "native_wifi_api_error",
                message: "failure",
                function: "WlanGetNetworkBssList",
                win32_code: 123
              }
            }
          )
        );

        expect(view.functionName).toBe(
          "WlanGetNetworkBssList"
        );
        expect(view.win32Code).toBe(123);
      }
    );
  }
);
