# INC-006: Cross-browser report validation

**Status:** Complete

## Delivered verification

- Native Chromium and Firefox execution in an isolated GitHub Actions job.
- Normal layout checks at 320, 375, 768 and 1440 CSS pixels in both engines.
- Enhanced checks at 320 CSS pixels with forced colors and WCAG text-spacing overrides.
- Assertions for page overflow, required sections, provenance banner, result table, keyboard skip
  navigation, next focus target, browser-console errors and prohibited external requests.
- Full-page screenshots and machine-readable JSON retained for 14 days.

## Evidence

GitHub Actions run `34777798680` passed both jobs. Artifact
`preflight-browser-matrix-34777798680` contains ten browser/viewport-mode results and screenshots.

## Claim boundary

This verifies the report's automated cross-browser acceptance requirements. It does not constitute
formal WCAG conformance or a human screen-reader assessment.
