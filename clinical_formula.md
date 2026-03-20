# OBSTETRIC BIOMETRICS: MATHEMATICAL COMPENDIUM
*Technical Documentation for the CradleMetrics Clinical Engine*

---

## SECTION I: MORPHOLOGICAL EXTRACTION
*Methods for transforming digital segmentation into standardized anatomical units.*

### [1.1] ELLIPTICAL CIRCUMFERENCE (HC & AC)
The circumference of the fetal head and abdomen is estimated using an elliptical model refined by Ramanujan’s second approximation.

$$ \boxed{ C \approx \pi(a + b) \left[ 1 + \left( \frac{3h}{10 + \sqrt{4 - 3h}} \right) \right] } $$

**Where:**
*   **C**: Final Circumference (mm)
*   **a**: Semi-major axis (one-half the diameter of the major axis)
*   **b**: Semi-minor axis (one-half the diameter of the minor axis)
*   **h**: Eccentricity parameter, defined as: $h = \frac{(a-b)^2}{(a+b)^2}$

**Rationale:** Digital ultrasound images are discrete grids. Simple pixel-counting leads to biased perimeters. Ellipse fitting provides a continuous mathematical abstraction that compensates for low-resolution edge noise.

---

### [1.2] GEODESIC LONG-BONE LENGTH (FL)
Linear longitudinal biometry is extracted via topological skeletonization of the femur mask.

$$ \boxed{ L = \max_{d}(P_{start} \to P_{end}) } $$

**Where:**
*   **L**: Femur Length (mm)
*   **d**: Geodesic distance along the medial axis (skeleton)
*   **P**: Endpoints of the skeletonized segment

**Rationale:** The femur is often curved or non-orthogonal to the probe. Straight-line Euclidean distance between bounding box corners underestimates the true bone length. Medial axis distance follows the anatomical curvature.

---

## SECTION II: PREDICTIVE DIAGNOSTICS
*Multi-variate regression models based on population-wide clinical data.*

### [2.1] ESTIMATED FETAL WEIGHT (EFW)
Calculation of mass is performed using the Hadlock 4-Parameter regression model.

$$ \boxed{ \log_{10}BW = 1.3596 - 0.00386(AC \times FL) + 0.0064(HC) + 0.00061(BPD \times AC) + 0.0424(AC) + 0.174(FL) } $$

**Parameters (in Centimeters):**
*   **BW**: Fetal Body Weight (grams)
*   **HC**: Head Circumference
*   **AC**: Abdominal Circumference
*   **BPD**: Biparietal Diameter
*   **FL**: Femur Length

**Clinical Note:** The AC parameter acts as the primary driver for mass estimation as it represents the liver size and glycogen stores which vary with weight.

---

### [2.2] CEPHALIC INDEX (CI)
A descriptive metric for the assessment of cephalic morphology (head shape).

$$ \boxed{ CI = \left( \frac{BPD}{OFD} \right) \times 100 } $$

**Parameters:**
*   **BPD**: Biparietal Diameter (Transverse)
*   **OFD**: Occipitofrontal Diameter (Longitudinal)

**Diagnostic Ranges:**
*   **Dolichocephaly**: $CI < 70\%$
*   **Mesocephaly**: $70\% \le CI \le 85\%$ (Normal)
*   **Brachycephaly**: $CI > 85\%$

---

## SECTION III: GROWTH STANDARDIZATION
*Assessment against diverse global reference populations.*

### [3.1] MULTI-STANDARD QUANTILE CLASSIFICATION
Measurements are normalized against a chosen reference population (WHO, Hadlock, or INTERGROWTH-21st).

$$ \boxed{ Z = \frac{X_{obs} - \text{Interp}(\text{Reference Tables}, GA)}{\text{Interp}(\text{SD Tables}, GA)} } $$

**Current Standards Library:**
*   **WHO**: Multinational reference for universal screening.
*   **INTERGROWTH-21st**: Longitudinal international standard.
*   **Hadlock**: Regression-derived gold standard for EFW and biometry.

---

## SECTION IV: ADVANCED CLINICAL SCREENING
*Cross-parameter validation for growth and hemodynamics.*

### [4.1] FETAL GROWTH RESTRICTION (FGR) CORRELATION
Composite screening combining morphometry and doppler.
*   **Metric**: $EFW < 10th \text{ percentile} \cap CPR < 1.08 \implies \text{High Risk FGR}$

### [4.2] RADIUS GUARD (GEOMETRIC SANITY)
Ensures diameter-circumference consistency.
*   **Rule**: $\text{BPD} \le \frac{HC}{\pi}$
*   **Rationale**: Prevents anatomical impossibilities due to segmentation artifacts.

### [4.3] ABDOMINAL WASTING INDEX
*   **Formula**: $\text{Ratio} = (FL / AC) \times 100$
*   **Normal**: 20.0 - 22.0
*   **Warning**: $> 23.5$
