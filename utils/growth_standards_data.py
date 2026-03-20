#!/usr/bin/env python3
"""
Fetal Growth Standards Reference Data
Comprehensive lookup tables for multiple clinical standards.
"""

# -----------------------------------------------------------------------------
# 1. INTERGROWTH-21st (International Standard)
# -----------------------------------------------------------------------------
INTERGROWTH_REFERENCE = {
    # Gestational Age (weeks): {HC, AC, FL, BPD}
    14: {'HC': 96, 'AC': 79, 'FL': 11, 'BPD': 26},
    16: {'HC': 124, 'AC': 103, 'FL': 18, 'BPD': 35},
    18: {'HC': 151, 'AC': 131, 'FL': 25, 'BPD': 42},
    20: {'HC': 176, 'AC': 158, 'FL': 32, 'BPD': 49},
    22: {'HC': 200, 'AC': 184, 'FL': 38, 'BPD': 55},
    24: {'HC': 222, 'AC': 209, 'FL': 44, 'BPD': 61},
    26: {'HC': 243, 'AC': 232, 'FL': 49, 'BPD': 66},
    28: {'HC': 263, 'AC': 254, 'FL': 54, 'BPD': 71},
    30: {'HC': 282, 'AC': 275, 'FL': 58, 'BPD': 75},
    32: {'HC': 300, 'AC': 295, 'FL': 62, 'BPD': 79},
    34: {'HC': 317, 'AC': 314, 'FL': 66, 'BPD': 83},
    36: {'HC': 333, 'AC': 332, 'FL': 69, 'BPD': 87},
    38: {'HC': 348, 'AC': 349, 'FL': 72, 'BPD': 90},
    40: {'HC': 362, 'AC': 365, 'FL': 75, 'BPD': 93},
}

INTERGROWTH_SD = {
    'HC': 12.0, 'AC': 15.0, 'FL': 4.0, 'BPD': 4.0
}

# -----------------------------------------------------------------------------
# 2. WHO Fetal Growth Charts (Multinational)
# -----------------------------------------------------------------------------
WHO_REFERENCE = {
    14: {'HC': 98, 'AC': 81, 'FL': 12, 'BPD': 27},
    16: {'HC': 128, 'AC': 106, 'FL': 20, 'BPD': 36},
    18: {'HC': 156, 'AC': 135, 'FL': 27, 'BPD': 43},
    20: {'HC': 182, 'AC': 164, 'FL': 34, 'BPD': 50},
    22: {'HC': 206, 'AC': 192, 'FL': 40, 'BPD': 56},
    24: {'HC': 228, 'AC': 220, 'FL': 46, 'BPD': 62},
    26: {'HC': 250, 'AC': 248, 'FL': 51, 'BPD': 67},
    28: {'HC': 270, 'AC': 275, 'FL': 56, 'BPD': 72},
    30: {'HC': 288, 'AC': 300, 'FL': 60, 'BPD': 76},
    32: {'HC': 304, 'AC': 322, 'FL': 64, 'BPD': 80},
    34: {'HC': 318, 'AC': 340, 'FL': 68, 'BPD': 84},
    36: {'HC': 331, 'AC': 354, 'FL': 71, 'BPD': 88},
    38: {'HC': 344, 'AC': 366, 'FL': 74, 'BPD': 91},
    40: {'HC': 355, 'AC': 375, 'FL': 77, 'BPD': 94},
}

WHO_SD = {
    'HC': 13.0, 'AC': 16.5, 'FL': 4.2, 'BPD': 4.1
}

# -----------------------------------------------------------------------------
# 3. HADLOCK (US/Universal Foundation)
# -----------------------------------------------------------------------------
HADLOCK_REFERENCE = {
    14: {'HC': 100, 'AC': 83, 'FL': 13, 'BPD': 28},
    16: {'HC': 130, 'AC': 109, 'FL': 21, 'BPD': 37},
    18: {'HC': 160, 'AC': 138, 'FL': 28, 'BPD': 44},
    20: {'HC': 185, 'AC': 168, 'FL': 35, 'BPD': 51},
    22: {'HC': 210, 'AC': 195, 'FL': 41, 'BPD': 57},
    24: {'HC': 230, 'AC': 222, 'FL': 47, 'BPD': 63},
    26: {'HC': 252, 'AC': 250, 'FL': 52, 'BPD': 68},
    28: {'HC': 272, 'AC': 276, 'FL': 57, 'BPD': 73},
    30: {'HC': 290, 'AC': 302, 'FL': 61, 'BPD': 77},
    32: {'HC': 306, 'AC': 324, 'FL': 65, 'BPD': 81},
    34: {'HC': 320, 'AC': 342, 'FL': 69, 'BPD': 85},
    36: {'HC': 334, 'AC': 358, 'FL': 72, 'BPD': 89},
    38: {'HC': 346, 'AC': 370, 'FL': 75, 'BPD': 92},
    40: {'HC': 358, 'AC': 380, 'FL': 78, 'BPD': 95},
}

HADLOCK_SD = {
    'HC': 10.0, 'AC': 14.0, 'FL': 3.5, 'BPD': 3.5
}

# Mapping of Standards
STANDARDS = {
    'INTERGROWTH': {'ref': INTERGROWTH_REFERENCE, 'sd': INTERGROWTH_SD, 'name': 'INTERGROWTH-21st'},
    'WHO': {'ref': WHO_REFERENCE, 'sd': WHO_SD, 'name': 'WHO Fetal Growth'},
    'HADLOCK': {'ref': HADLOCK_REFERENCE, 'sd': HADLOCK_SD, 'name': 'Hadlock (Universal)'}
}
