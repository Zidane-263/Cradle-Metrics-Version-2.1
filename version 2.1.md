# CradleMetrics Version 2.1 - Release Notes
## "The Workspace Optimization Update" (March 20, 2026)

Building upon the clinical foundation of Version 2.0, this update focuses on professional workflow efficiency, multi-standard diagnostic flexibility, and system-wide stability. Version 2.1 transforms the CradleMetrics dashboard into a high-throughput workstation for rapid biometric re-evaluation and population health tracking.

---

### 🏥 1. Workstation Workflow Refactoring
Optimized the primary assessment interface to align with high-cadence clinical workflows.
- **Dynamic Analysis Controls**: Replaced static PDF buttons in the biometric card with **"New Analysis"** (workspace reset) and **"Analyse Again"** (instant re-valuation) buttons.
- **Header-Centric Reporting**: Consolidated "View PDF" and "Download PDF" actions into the results header strip, ensuring the report is only generated once the assessment is finalized.
- **Clean UI Density**: Further reduced layout friction by removing redundant buttons and centering focus on the AI-extracted biometrics.

### ⚙️ 2. Real-Time Growth Standard Switching
Introduced a first-of-its-kind "Diagnostic Toggle" for comparative biometry.
- **Instant Standard Re-evaluation**: A new settings panel (accessible via the Gear Icon) allows examiners to switch between **INTERGROWTH-21st**, **WHO Fetal Growth**, and **Hadlock (Universal)** standards after the analysis is complete.
- **Live Percentile Updates**: Switching standards instantly re-triggers the clinical rules engine, updating all biometric percentiles and risk classifications without requiring a re-upload of the image.
- **Workstation Settings Overlay**: Engineered a non-intrusive settings dropdown anchored directly to the biometric workstation card.

### 📊 3. Population Health Analytics
Enhanced the Patient Directory from a lookup tool into a population-level insights dashboard.
- **Comparative KPIs**: The patient directory now features live, populated cards for **Total Database Size**, **Risk Prevalence (%)**, and **Average Gestational Age**.
- **Telemetry Persistence**: Fixed data indexing to ensure every scan correctly archives the **Consensus GA** and **Risk Status** for immediate visibility in the directory view.
- **Audit-Ready History**: Improved the synchronization between the `ClinicalHistoryManager` and the frontend directory to ensure zero-latency record retrieval.

### 🛡️ 4. AI Backend Hardening (Stability+)
implemented deep-level guardrails to prevent runtime failures during high-stress processing.
- **Bounding Box Validation**: Added a strict validation layer to the `SAMSegmentor` to catch and skip invalid or zero-sized detection boxes before they reach the deep learning layer.
- **Crash Prevention**: Specifically addressed the `repeat_interleave` tensor error by ensuring no `NoneType` or malformed data is passed to the AI segmentation masks.
- **Boundary Guardrails**: Implemented coordinate clipping to ensure all AI-detected landmarks stay within the physical image bounds.

### 📈 5. High-Fidelity Chart Capture
Ensured that the generated clinical reports always reflect the full diagnostic picture.
- **Off-Screen Rendering**: Upgraded the PDF engine to reliably capture the **Longitudinal Growth Trends** chart even if the examiner has not explicitly navigated to the "Growth Trends" tab.
- **Visual Consistency**: Locked chart dimensions for report inclusion to ensure a professional 16:9 aspect ratio regardless of the user's screen resolution.

### ✨ 6. Professional UX & Nomenclature
- **Clinical Labeling**: Refined biometric output names from raw database keys (e.g., `head_aspect_ratio`, `humerus_length`) into formatted, professional medical labels.
- **Persistent States**: Improved URL parameter synchronization (`file_id`) to ensure that re-analyzing an image maintains a consistent session across all workstation tabs.

---
**Status**: Stable & Deployment Ready
**Current Release**: 2.1.0-Patch
