# BUG REPORT 1

## Bug A – iOS App Freezes When Adding >10 Waypoints

### Title

iOS app becomes unresponsive for 3–5 seconds when adding more than 10 waypoints to a trip

---

### Description

When a user adds more than 10 waypoints to a trip, the application freezes for approximately 3–5 seconds before rendering the updated list of waypoints. This issue occurs consistently on iOS devices and does not reproduce on Android.

This suggests a potential platform-specific performance bottleneck or UI thread blocking operation.

---

### Environment

* **Platform:** iOS
* **Devices Tested:** iPhone 12, iPhone 14
* **OS Version:** iOS 17.x
* **App Version:** [Insert version]
* **Network:** WiFi + 5G (reproducible on both)

---

### Steps to Reproduce

1. Launch iOS app
2. Log in
3. Create new trip
4. Add waypoints sequentially
5. Add 11th waypoint

---

### Expected Behavior

* Waypoints should render immediately (<1 second delay)
* UI remains responsive
* No blocking or visible freezing

---

### Actual Behavior

* App freezes for 3–5 seconds
* UI becomes non-interactive
* After delay, all waypoints appear

---

### Reproducibility

100% on tested iOS devices
0% on Android (Pixel 6 tested)

---

### Severity

**Major**

Reasoning:
The app does not crash, but the freeze significantly degrades user experience and may be interpreted as instability.

---

### Priority

**High**

Reasoning:
Trip planning is a core feature. Performance degradation in core workflow impacts retention and user trust.

---

### Suspected Root Cause

Potential causes:

* UI thread blocked during waypoint list re-render
* Inefficient diffing or full list re-render after 10 items
* N+1 API calls triggered after threshold
* Inefficient layout recalculation in iOS rendering engine
* Missing list virtualization

Recommend profiling using:

* Xcode Instruments (Time Profiler)
* Main Thread Checker
* Network inspection

---

### Recommendation

* Profile rendering after 10+ items
* Implement list virtualization or incremental rendering
* Offload heavy operations from main thread
* Benchmark waypoint addition time across thresholds (5, 10, 15, 20)

---

---

# BUG REPORT 2

## Bug B – Search Fails to Respect Diacritical Characters

---

### Title

Search returns incorrect or incomplete results when query contains diacritical marks (e.g., "Café Rouge")

---

### Description

Search functionality does not return expected results when searching for attractions containing special characters or diacritics.

Example:
Searching for “Café Rouge” produces different results compared to “Cafe Rouge”.

This indicates improper normalization or inconsistent character handling in the search index.

---

### Environment

* Platform: iOS & Android
* Devices: iPhone 14, Pixel 6
* App Version: [Insert version]
* Network: WiFi

---

### Steps to Reproduce

1. Open search
2. Enter: “Café Rouge”
3. Record results
4. Clear search
5. Enter: “Cafe Rouge”
6. Compare results

---

### Expected Behavior

Search should:

* Normalize diacritical characters
* Return identical or equivalent results
* Support UTF-8 characters

---

### Actual Behavior

* Results differ
* Some expected attractions missing
* Appears diacritics are ignored or mishandled

---

### Reproducibility

Consistent across devices

---

### Severity

**Major**

Reasoning:
Search reliability is critical to discoverability. Incorrect results impact user trust and usability.

---

### Priority

**Medium–High**

Reasoning:
Does not block core workflow but degrades core feature quality.

---

### Suspected Root Cause

Potential issues:

* Search index not normalized
* Backend not applying Unicode normalization (NFC/NFD)
* Frontend query not sanitized
* Database collation misconfiguration

---

### Recommendation

* Normalize both indexed data and search input
* Apply Unicode normalization (NFKD)
* Strip diacritics consistently
* Add automated tests for multilingual queries
* Review DB collation settings

---

---

# BUG REPORT 3

## Derived Issue – Inconsistent Search Index Behavior Across Platforms

---

### Title

Search results inconsistent between iOS and Android for identical queries

---

### Description

While investigating Bug B, an inconsistency was observed:

* Some queries produce slightly different ordering or result counts between iOS and Android.

This suggests potential client-side filtering, caching, or API parameter differences.

---

### Environment

* iPhone 14 – iOS 17
* Pixel 6 – Android 14
* App Version: Same build

---

### Steps to Reproduce

1. On iOS, search “Café”
2. Record top 5 results
3. On Android, repeat identical query
4. Compare ordering and count

---

### Expected Behavior

Search results should be identical across platforms if using the same backend endpoint.

---

### Actual Behavior

* Result ordering differs
* Minor count discrepancy observed

---

### Severity

**Medium**

---

### Priority

**Medium**

---

### Hypothesis

* Platform-specific API parameters
* Client-side sorting differences
* Cached search responses
* Inconsistent pagination handling

---

### Recommendation

* Verify API request parity between platforms
* Log backend response payload comparison
* Centralize sorting logic on server
* Add integration test for search parity

---

---

# Email to Engineering Manager

Below is a clean, professional email suitable for submission:

---

Subject: Mobile App Defects Identified During Trip & Search Testing

Hi [Engineering Manager Name],

During testing of the mobile application, I identified two primary issues and one related search inconsistency that warrant investigation.

1. iOS Performance Issue – Adding more than 10 waypoints results in a 3–5 second UI freeze. This appears to be a main-thread blocking or rendering inefficiency specific to iOS.

2. Search Normalization Issue – Queries containing diacritical characters (e.g., “Café”) return inconsistent results compared to non-accented equivalents.

3. Cross-Platform Search Parity – Minor inconsistencies in search result ordering were observed between iOS and Android.

The waypoint issue is high priority due to impact on core trip-planning flow. The search issues affect discoverability and internationalization support.

I’ve included detailed reproduction steps, severity assessments, and potential root cause hypotheses in the attached reports.

Please let me know if you’d like performance profiling data or API logs captured for further investigation.

Best,
[My Name]

---
