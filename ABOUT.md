# 🩺 CradleMetrics — Complete Project Documentation

> An AI-powered fetal ultrasound analysis system for automated biometric extraction, clinical risk assessment, and longitudinal growth tracking.

---

## 📋 Table of Contents

1. [What is CradleMetrics?](#1-what-is-cradlemetrics)
2. [Why Was It Built?](#2-why-was-it-built)
3. [System Architecture](#3-system-architecture)
4. [How the Pipeline Works](#4-how-the-pipeline-works)
5. [Biometric Measurements Extracted](#5-biometric-measurements-extracted)
6. [Measurement Formulas](#6-measurement-formulas)
7. [Clinical Standards Used](#7-clinical-standards-used)
8. [The Growth Chart Explained](#8-the-growth-chart-explained)
9. [Percentile Bands — What They Mean](#9-percentile-bands--what-they-mean)
10. [INTERGROWTH-21st Standard In Detail](#10-intergrowth-21st-standard-in-detail)
11. [WHO Fetal Growth Standard](#11-who-fetal-growth-standard)
12. [Hadlock Standard](#12-hadlock-standard)
13. [Clinical Risk Classification](#13-clinical-risk-classification)
14. [Growth Patterns & Conditions Detected](#14-growth-patterns--conditions-detected)
15. [Predictive Growth Forecasting](#15-predictive-growth-forecasting)
16. [Additional Clinical Metrics](#16-additional-clinical-metrics)
17. [Longitudinal Tracking](#17-longitudinal-tracking)
18. [Advanced Analytics & Clinical Decision Support](#18-advanced-analytics--clinical-decision-support)
19. [Tech Stack](#19-tech-stack)

---

## 1. What is CradleMetrics?

**CradleMetrics** is an automated fetal health analytics platform that processes raw obstetric ultrasound images and produces a full clinical assessment — without requiring any manual measurement by the user.

You simply upload a fetal ultrasound image, optionally enter the gestational age, and the system:

- Detects fetal body parts using a custom-trained AI model
- Segments the detected organs with pixel-level precision
- Extracts biometric measurements (head, abdomen, femur, etc.)
- Compares those measurements against international clinical standards
- Generates a complete clinical report with risk levels, growth classification, and future growth predictions

---

## 2. Why Was It Built?

Routine fetal biometric measurement is one of the most important and time-consuming tasks in obstetrics. Errors in manual measurement can go undetected and lead to missed diagnoses of Fetal Growth Restriction (FGR), macrosomia, or structural defects.

**CradleMetrics addresses:**

- ⏱️ **Speed** — Reduces analysis time from minutes to seconds
- 🔁 **Consistency** — Eliminates inter-operator measurement variability
- 🌍 **Access** — Can be deployed in settings without specialist sonographers
- 📈 **Longitudinal Insight** — Tracks growth across multiple scans for the same patient
- 📊 **Evidence-based** — Benchmarks against three peer-validated international standards

---

## 3. System Architecture

```
Ultrasound Image
       │
       ▼
┌─────────────────┐
│  YOLOv8 Detector│  ← Detects bounding boxes: Head, Abdomen, Arm, Legs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SAM Segmentor  │  ← Segment Anything Model creates pixel-level masks
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Biometric Extractor    │  ← Calculates HC, AC, FL, BPD from masks
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Clinical Assessment    │  ← Compares with INTERGROWTH/WHO/Hadlock
│  Engine                 │  ← Calculates percentiles, Z-scores, EFW
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Flask Web Dashboard    │  ← Interactive results + growth charts
└─────────────────────────┘
```

---

## 4. How the Pipeline Works

### Step 1 — YOLO Detection
The image is passed through a **custom-trained YOLOv8 model** that identifies and draws bounding boxes around anatomical structures:
- The **head** (for HC, BPD)
- The **abdomen** (for AC)
- The **femur/legs** (for FL)
- The **arm** (for limb length)

Only detections above the confidence threshold (default: **50%**) are accepted.

### Step 2 — SAM Segmentation
For each detected bounding box, **Meta's Segment Anything Model (SAM ViT-B)** generates a precise pixel-by-pixel mask over that anatomy. This is what allows us to trace the exact outline of, for example, the fetal head and compute its circumference.

### Step 3 — Biometric Extraction
Using the pixel masks, the engine computes real-world measurements by:
1. Tracing the contour of each mask
2. Computing the perimeter / diameter / length of each structure
3. Converting from pixels to millimetres using a user-configurable **calibration factor** (default: 2.5 px/mm)

### Step 4 — Clinical Assessment
Each biometric value is fed into the Clinical Rules Engine, which:
- Computes **Z-scores** (how far the measurement is from the population mean in standard deviations)
- Derives **percentile positions** using a normal distribution model
- Classifies each measurement against clinical guidelines
- Detects growth restriction, macrosomia, microcephaly etc.
- Optionally computes Doppler and AFI assessments if entered manually

### Step 5 — Report & Visualization
A dashboard displays all results in real-time with color-coded risk indicators, radar charts, and growth trend charts compared to international standards.

---

## 5. Biometric Measurements Extracted

| Abbreviation | Full Name | What It Measures | Unit |
|---|---|---|---|
| **HC** | Head Circumference | Outer perimeter of the fetal skull | mm |
| **AC** | Abdominal Circumference | Outer perimeter of the fetal abdomen at the liver level | mm |
| **BPD** | Biparietal Diameter | Width of the skull from parietal bone to parietal bone | mm |
| **FL** | Femur Length | Length of the thigh bone (longest bone in the body) | mm |
| **EFW** | Estimated Fetal Weight | Calculated weight estimate derived from biometrics | grams |

### Why These Four?

These four measurements form the **gold standard** fetal biometry set, universally adopted since the 1970s Hadlock studies. Together they give a comprehensive picture of fetal growth because:

- **HC** reflects brain and skull development
- **AC** is the most sensitive indicator of fetal nutrition and adiposity
- **BPD** is the oldest and most reproducible measurement
- **FL** reflects skeletal maturation and longitudinal growth

---

## 6. Measurement Formulas

### Head Circumference (HC)
Computed from the pixel contour traced by the SAM mask:
```
HC = (Perimeter of head contour mask) × calibration_factor
```
Or from ellipse fitting (more stable):
```
HC = π × √( (a² + b²) / 2 )
```
where `a` = semi-major axis, `b` = semi-minor axis of the fitted ellipse.

---

### Biparietal Diameter (BPD)
```
BPD = width of minimum bounding box across head mask × calibration_factor
```

---

### Abdominal Circumference (AC)
Computed identically to HC but from the abdomen mask:
```
AC = (Perimeter of abdomen contour mask) × calibration_factor
```

---

### Femur Length (FL)
```
FL = length of the longest line segment fitting inside the femur mask
   = √( (x₂ - x₁)² + (y₂ - y₁)² ) × calibration_factor
```

---

### Estimated Fetal Weight (EFW) — Hadlock 4-Parameter Formula
The industry standard formula published by Hadlock (1985):

```
log₁₀(EFW) = 1.3596
           − 0.00386 × (AC × FL)
           + 0.0064  × HC
           + 0.00061 × (BPD × AC)
           + 0.0424  × AC
           + 0.174   × FL

EFW (grams) = 10^(log₁₀EFW)
```
Where all measurements are in **centimetres**.

> This formula achieves ±15% weight accuracy across the full gestational range and is the most widely used EFW formula globally.

---

### Cephalic Index (CI)
```
CI = (BPD / OFD) × 100
```
Where **OFD** (Occipito-Frontal Diameter) is either measured directly or estimated:
```
OFD ≈ (2 × HC / π) − BPD
```

| CI Value | Classification | Meaning |
|---|---|---|
| < 70 | Dolichocephalic | Long, narrow head |
| 70 – 86 | Mesocephalic (Normal) | Normal skull shape |
| > 86 | Brachycephalic | Wide, short head |

---

### HC/AC Ratio
```
HC/AC = HC / AC
```
Normal ratio is approximately **1.0** at ≈20 weeks, dropping to ≈0.97 at term. A significantly elevated HC/AC (>1.2) with low AC percentile is a classic sign of **asymmetric IUGR** — suggesting brain-sparing at the expense of abdominal growth.

---

### FL/AC Ratio
```
FL/AC = (FL / AC) × 100
```
Normal range: ~20–22. Values > 23.5 may indicate abdominal wasting or growth restriction.

---

## 7. Clinical Standards Used

The system supports three internationally validated fetal growth standards that you can switch between:

### 🌐 INTERGROWTH-21st (Default)
### 🌐 WHO Fetal Growth Charts
### 🇺🇸 Hadlock (USA/Universal)

For each standard, reference values for **HC, AC, FL, BPD** are stored at 2-week intervals from **14 to 40 weeks** of gestation, along with a standard deviation (SD) value per metric.

---

## 8. The Growth Chart Explained

The longitudinal growth chart displays **three key elements:**

### 🔵 Patient Data (Cyan Line)
The actual measurements calculated from the ultrasound image plotted over gestational weeks. Each dot is one scan session. If multiple scans are saved for the same patient, they connect into a trajectory line.

### 💜 Growth Forecast (Purple Dashed Line)
A **predictive extension** of the patient's current growth trajectory, projected 4 weeks forward. This shows where the baby is likely to be if the current growth pattern continues — helping clinicians anticipate issues proactively.

For a single scan, forecasting uses **Z-score projection** (described below). For multiple scans, it uses **linear regression** through the data points.

### ⚪ Reference Percentile Bands (White/Red Lines)
Three curves from the selected clinical standard (e.g. INTERGROWTH-21st):
- **50th Percentile** (dashed white) — The average/median for the general population
- **10th Percentile** (dashed red) — Lower boundary of normal range
- **90th Percentile** (dashed red) — Upper boundary of normal range

The shaded area between 10th and 90th percentile represents **the normal range** for fetal growth.

---

## 9. Percentile Bands — What They Mean

### The Simple Analogy

Imagine you could gather **100 healthy babies all at exactly the same gestational age** — say, all exactly 28 weeks old. You measure their Head Circumferences and line them up in order, from the smallest to the largest:

```
Baby #1 (smallest HC)  ──→  Baby #50 (average HC)  ──→  Baby #100 (largest HC)
```

Every baby in that lineup has a **percentile rank** that tells you where they sit in that group.

- **Baby #1** is at the **1st percentile** — only 1% of babies have a smaller head.
- **Baby #50** is at the **50th percentile** — exactly the average. Half the babies are smaller, half are larger.
- **Baby #100** is at the **100th percentile** — the biggest in the group.

That's all a percentile is — a **rank position** within a healthy reference population.

---

### The Three Lines on the Chart

The growth chart shows **three reference lines** drawn from the clinical standard (INTERGROWTH-21st, WHO, or Hadlock):

#### ⚪ 50th Percentile — The Middle Dashed White Line
This is the **population median** — the expected measurement for an average healthy fetus at each gestational week.

- A measurement sitting exactly on this line = perfectly average for its age.
- Most healthy babies naturally track slightly above or below this line — that is completely normal.
- It is **not** a target that every baby must hit. Constitutionally small or large babies can be perfectly healthy at the 20th or 70th percentile throughout pregnancy.

#### 🔴 10th Percentile — The Lower Dashed Red Line
This is the **lower boundary of normal**.

- 10% of healthy reference babies fall below this line — so a measurement below the 10th percentile is smaller than 90% of healthy babies the same age.
- When a measurement drops **below** this line, it enters the zone where clinical review is warranted.
- A single dip below the 10th is not automatically alarming — but combined with a **downward crossing trend** (the measurement falling across multiple percentile bands over time), it signals possible **Fetal Growth Restriction (FGR) or IUGR**.

#### 🔴 90th Percentile — The Upper Dashed Red Line
This is the **upper boundary of normal**.

- 10% of healthy reference babies fall above this line.
- A measurement consistently **above** the 90th percentile suggests the fetus is growing larger than expected, which can indicate **macrosomia** (excessive size), often associated with gestational diabetes.

---

### The Normal Zone (The Safe Band)

```
                  ┌────────────────────────────────────────────┐
90th ─────────────┤                                            ├─── upper red line
                  │  ✅  THE NORMAL GROWTH ZONE (10th–90th)   │
                  │                                            │
50th - - - - - - -│- - - - - - - Average - - - - - - - - - - │- - white dashed
                  │                                            │
10th ─────────────┤                                            ├─── lower red line
                  └────────────────────────────────────────────┘
              14w    18w    22w    26w    30w    34w    38w    40w (Gestational Age)
```

The **shaded region between the 10th and 90th percentile** is the normal, healthy growth zone. As long as the patient's cyan data line stays inside this band, the fetus is growing appropriately.

---

### What Each Specific Percentile Value Means

| Percentile Position | What It Tells You | Clinical Action |
|---|---|---|
| **> 97th** 🔴 | Only 3% of babies are larger — severe macrosomia zone | Urgent specialist review |
| **95th – 97th** 🟡 | Large but not critical — top 5% | Macrosomia monitoring, check for gestational diabetes |
| **90th – 95th** 🟡 | Borderline large — top 10% | Monitor, repeat scan in 2–4 weeks |
| **10th – 90th** ✅ | **Normal range** — 80% of healthy babies fall here | Routine care |
| **5th – 10th** 🟡 | Borderline small — bottom 10% | Close monitoring, possible early FGR |
| **3rd – 5th** 🔴 | Small — bottom 5% | High concern for growth restriction, referral recommended |
| **< 3rd** ⛔ | Severely small — bottom 3% | Urgent evaluation — significant FGR risk |

---

### Why Percentile Alone Is Not Enough

A critical clinical principle: **percentile must always be interpreted alongside the growth trend**.

**Example 1 — Stable at 8th Percentile:**
A baby consistently measuring at the 8th percentile from week 20 to week 36 is likely just **constitutionally small**. The growth trajectory is parallel to the reference curve — it's just tracking low. This may be completely normal.

**Example 2 — Falling from 40th to 8th Percentile:**
A baby that was measuring at the 40th percentile at week 22 but has dropped to the 8th percentile by week 30 has crossed four percentile bands downward. This **falling trajectory** is a far more significant warning sign than the absolute percentile value. This is called **"growth faltering"** and warrants urgent investigation.

```
Scenario A (Stable low): NORMAL-ISH        Scenario B (Falling): CONCERNING ⚠️
                                           
  50th ─────────────────────────           50th ──────────────────────────
                                                                   ╲
  10th ──────────────────────────           10th ────────────────── ╲────
         ● ─ ─ ● ─ ─ ● ─ ─ ●                    ●─ ─●─ ─ ●─ ─●
      (Tracking parallel to band)              (Crossing bands downward)
```

This is why **longitudinal tracking across multiple scans** (Section 17) is so important — a single reading in isolation can be misleading.

> **Important:** Percentile classification is a **clinical screening tool**, not a diagnosis. All results from CradleMetrics must be reviewed and interpreted by a qualified healthcare professional.

---


## 10. INTERGROWTH-21st Standard In Detail

**INTERGROWTH-21st** (International Newborn Growth Project for the 21st Century) is the most modern and rigorous international fetal growth standard, published in 2014.

### Background
Conducted in **8 countries** across 4 continents (Brazil, China, India, Italy, Kenya, Oman, UK, USA), this landmark study recruited over **4,600 pregnant women** who were:
- Healthy with optimal nutrition
- No tobacco, alcohol, or drug use
- Living at low altitude
- Receiving regular prenatal care
- Free of pregnancy complications

The goal was to define how **all babies should grow** when health conditions are optimal — not just how babies in one country typically grow.

### Why It's the Preferred Standard
- **Prescriptive standard** → defines optimal growth, not just typical growth
- Shows that fetal growth potential is essentially the same across all ethnicities when health conditions are controlled
- Endorsed by **WHO, FIGO, RCOG**, and obstetric societies worldwide
- More accurate than country-specific charts for detecting true pathological growth restriction

### Reference Values (50th Percentile — mm)

| GA (weeks) | HC | AC | FL | BPD |
|---|---|---|---|---|
| 14 | 96 | 79 | 11 | 26 |
| 18 | 151 | 131 | 25 | 42 |
| 22 | 200 | 184 | 38 | 55 |
| 26 | 243 | 232 | 49 | 66 |
| 28 | 263 | 254 | 54 | 71 |
| 32 | 300 | 295 | 62 | 79 |
| 36 | 333 | 332 | 69 | 87 |
| 40 | 362 | 365 | 75 | 93 |

### Standard Deviations (INTERGROWTH-21st)
| Metric | SD (mm) |
|---|---|
| HC | ± 12.0 |
| AC | ± 15.0 |
| FL | ± 4.0 |
| BPD | ± 4.0 |

---

## 11. WHO Fetal Growth Standard

The **WHO Fetal Growth Charts (2017)** are an alternative multinational standard, developed from a large prospective study conducted in **10 countries**. Compared to INTERGROWTH-21st:

- Slightly larger reference values at later gestational ages
- AC reference values tend to be higher from 28 weeks onward
- Wider standard deviations, reflecting more population diversity

| Metric | SD (mm) |
|---|---|
| HC | ± 13.0 |
| AC | ± 16.5 |
| FL | ± 4.2 |
| BPD | ± 4.1 |

Use WHO when working with population groups or clinical settings where WHO guidance is the governing standard.

---

## 12. Hadlock Standard

The **Hadlock (1984/1985)** charts are the original and most historically widespread growth standards, derived from studies in the **United States**.

- Published by Dr. Frank P. Hadlock at the University of Texas
- Based on a predominantly North American population
- Widely used in US/Canadian clinical practice
- Still the basis for many commercial ultrasound machine default charts

| Metric | SD (mm) |
|---|---|
| HC | ± 10.0 |
| AC | ± 14.0 |
| FL | ± 3.5 |
| BPD | ± 3.5 |

The Hadlock standard also provides the foundational **EFW formula** used across all three standards in this system.

---

## 13. Clinical Risk Classification

The system uses a 4-level risk model:

| Level | Color | Meaning |
|---|---|---|
| 🟢 **Normal** | Green | All measurements within 10th–90th percentile |
| 🟡 **Borderline** | Amber | 5th–10th or 90th–95th percentile — monitor closely |
| 🔴 **High Risk** | Red | Below 5th or above 95th — clinical review needed |
| ⛔ **Critical** | Dark Red | Below 3rd or above 97th — urgent evaluation |

---

## 14. Growth Patterns & Conditions Detected

### ✅ AGA — Appropriate for Gestational Age
All measurements (especially AC) fall within the 10th–90th percentile. Normal growth. No action needed beyond routine care.

### 📉 IUGR — Intrauterine Growth Restriction
The AC is below the **10th percentile**, indicating the fetus is not growing adequately. Two subtypes:

- **Symmetric IUGR** — All measurements proportionally small (often early onset, may indicate chromosomal issues)
- **Asymmetric IUGR** — HC relatively preserved but AC is very small. The HC/AC ratio is elevated (> 1.2). This is **"brain-sparing"** — the fetus redirects blood flow to protect the brain while the body suffers nutrient deprivation. This is the most common IUGR type.

### 📈 Macrosomia — Large for Gestational Age
AC is above the **90th percentile**. The fetus is growing excessively, often associated with gestational diabetes. EFW > 4000g is a clinical threshold.

### 🧠 Microcephaly
HC is below the **5th percentile** while other measurements are normal. Indicates abnormally small brain development.

### 🏋️ FGR (Fetal Growth Restriction) with Doppler Correlation
When EFW is below the 10th percentile AND the **Cerebroplacental Ratio (CPR)** is abnormal (CPR < 1.08), this is a **HIGH PRIORITY** combination suggesting significant placental insufficiency.

---

## 15. Predictive Growth Forecasting

For each scan, the system projects 4 weeks forward on the growth chart.

### When 2+ Scans Exist (Multi-Scan Regression)
A **linear regression** is computed through all historical data points:
```
y = slope × GA + intercept
```
Where `y` is the predicted biometric value at future gestational weeks. This directly extrapolates the patient's personal growth trajectory.

### When Only 1 Scan Exists (Z-Score Projection)
Since there is only one data point, we can't compute a trend. Instead, the system:

1. Finds what **Z-score** the patient's measurement has relative to the standard at current GA:
   ```
   Z = (measured_value − mean_at_GA) / SD
   ```

2. Applies that same Z-score to future weeks on the standard curve:
   ```
   predicted_value_at_future_GA = mean_at_future_GA + (Z × SD_at_future_GA)
   ```

This assumes the baby will **track parallel to the reference standard**, maintaining its relative position. E.g., if the baby is currently at the 30th percentile, it's predicted to stay near the 30th percentile in future weeks.

---

## 16. Additional Clinical Metrics

### Amniotic Fluid Index (AFI)
Manually entered. Classified as:
- **< 5 cm** → Oligohydramnios (dangerously low fluid)
- **5–25 cm** → Normal
- **> 25 cm** → Polyhydramnios (excess fluid)

### Doppler — Cerebroplacental Ratio (CPR)
Evaluates blood flow distribution between the uterine artery (UA-PI) and middle cerebral artery (MCA-PI):
```
CPR = MCA-PI / UA-PI
```
- **CPR > 1.08** → Normal blood flow distribution
- **CPR ≤ 1.08** → Abnormal — possible fetal compromise / brain-sparing

### EFW Percentile
```
ln(mean_EFW) = 0.578 + (0.332 × GA) − (0.00354 × GA²)
SD_EFW ≈ mean_EFW × 0.15   (15% of mean, per clinical convention)
Z = (measured_EFW − mean_EFW) / SD_EFW
Percentile = Φ(Z) × 100
```
Where `Φ` is the standard normal cumulative distribution function.

### Image Quality Score
An automated score (0–100) assessing:
- YOLO detection confidence
- Head plane aspect ratio (ideally 0.70–0.94 for a true transverse plane)
- Abdomen circularity (ideally 0.80–1.25)

| Score | Status |
|---|---|
| ≥ 85 | Excellent |
| 70–84 | Good |
| 50–69 | Fair |
| < 50 | Poor |

---

## 17. Longitudinal Tracking

When scans are saved under the same **Patient ID**, all historical measurements are stored in `clinical_history/` using a JSON-based persistence system. The system then:

- Displays all past scan points on the growth chart connected as a trajectory
- Calculates **Growth Velocity** (rate of measurement increase per week between scans)
- Detects trend changes — a fetus crossing percentile bands downward is a warning sign even if still "within range"
- Saves a full index (`index.json`) of all patient scan records with timestamps and GA values

---

## 18. Advanced Analytics & Clinical Decision Support

CradleMetrics 2.0+ includes high-level predictive and diagnostic tools designed to assist in obstetric decision-making at a glance.

### Estimated Delivery Date (EDD)
Calculated based on the latest consensus Gestational Age (GA) and the current scan date.
```
EDD = Scan_Date + (280 − (GA_weeks × 7)) days
```
The result provides the predicted birth date and the number of weeks remaining.

### Growth Faltering Detection (Percentile Drop)
The system alerts clinicians if a patient crosses **2 or more percentile bands downward** between scans (e.g., from the 75th to the 25th). 
- **Rule**: If `Percentile_Previous − Percentile_Latest > 40`, a "Faltering Alert" is triggered.
- Monitored for HC, AC, BPD, and FL.

### Predicted Birth Weight (at 40w)
Using current growth velocity (EFW increase per week), the system projects the weight at the 40-week milestone.
- **Macrosomia Warning**: Triggered if predicted birth weight ≥ 4,000g.
- **SGA Warning**: Triggered if predicted birth weight < 2,500g.

### Gestational Age (GA) Consensus & Consistency
Instead of a single GA, the system calculates GA independently for each biometric (HC-GA, AC-GA, etc.) and evaluates their consistency.
- **Excellent Consistency**: Variance < 0.5 weeks between all landmarks.
- **Fair/Poor Consistency**: Variance > 1.0 weeks — suggests asymmetric growth or measurement error.

### Next Scan Recommendation
An algorithmic recommendation for the ideal follow-up date based on current clinical risk:
| Risk Level | Recommended Follow-up | Reason |
|---|---|---|
| **Critical** | Within 24-48 hours | Immediate clinical review required |
| **High Risk** | 1-2 weeks | Weekly monitoring of growth velocity |
| **Borderline** | 2-4 weeks | Close interval monitoring |
| **Normal** | 4-6 weeks | Routine prenatal care |

---

## 19. Tech Stack

| Component | Technology |
|---|---|
| AI Detection | **YOLOv8** (Ultralytics) — Custom trained on fetal ultrasound dataset |
| AI Segmentation | **SAM ViT-B** (Meta Segment Anything Model) |
| Backend | **Python 3.10 + Flask** |
| Clinical Engine | Custom **clinical_rules.py** — Z-scores, EFW, Doppler, AFI |
| Growth Standards | **INTERGROWTH-21st, WHO, Hadlock** — Implemented in `utils/growth_standards.py` |
| Frontend | Vanilla **HTML/CSS/JavaScript** |
| Charts | **Chart.js** with custom animation and interactive tooltips |
| History Storage | File-based **JSON** persistence (no external database) |
| Report Generation | PDF + **CSV** export via ReportLab and Python's csv module |

---

*CradleMetrics — Bringing evidence-based fetal biometry assessment powered by artificial intelligence.*
