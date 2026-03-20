#!/usr/bin/env python3
"""
Fetal Growth Standards Provider
Generic calculator supporting multiple clinical standards (WHO, Hadlock, INTERGROWTH).
"""

import numpy as np
from scipy import stats, interpolate
from typing import Dict, Optional, Tuple
from utils.growth_standards_data import STANDARDS


class FetalGrowthProvider:
    """
    Generic fetal growth calculator that can switch between different clinical standards.
    """
    
    def __init__(self, standard_id: str = 'INTERGROWTH'):
        """
        Initialize growth provider with a specific standard.
        
        Args:
            standard_id: One of 'INTERGROWTH', 'WHO', 'HADLOCK'
        """
        if standard_id not in STANDARDS:
            print(f"Warning: Standard {standard_id} not found. Defaulting to INTERGROWTH.")
            standard_id = 'INTERGROWTH'
            
        self.standard_id = standard_id
        self.standard_info = STANDARDS[standard_id]
        self.reference = self.standard_info['ref']
        self.sd = self.standard_info['sd']
        self.display_name = self.standard_info['name']
        self.valid_metrics = ['HC', 'AC', 'FL', 'BPD']
        
        # Create interpolation functions for each metric
        self.interpolators = {}
        for metric in self.valid_metrics:
            gas = sorted(self.reference.keys())
            values = [self.reference[ga][metric] for ga in gas]
            self.interpolators[metric] = interpolate.interp1d(
                gas, values, kind='cubic', fill_value='extrapolate'
            )
    
    def get_expected_value(self, ga_weeks: float, metric_type: str) -> float:
        """Get expected (50th percentile) value for GA"""
        if metric_type not in self.valid_metrics:
            raise ValueError(f"Invalid metric. Must be one of {self.valid_metrics}")
        
        return float(self.interpolators[metric_type](ga_weeks))
    
    def calculate_z_score(self, measurement: float, ga_weeks: float, 
                          metric_type: str) -> float:
        """Calculate Z-score"""
        expected = self.get_expected_value(ga_weeks, metric_type)
        sd = self.sd[metric_type]
        return (measurement - expected) / sd
    
    def calculate_percentile(self, measurement: float, ga_weeks: float, 
                             metric_type: str) -> float:
        """Calculate percentile using normal distribution"""
        z_score = self.calculate_z_score(measurement, ga_weeks, metric_type)
        percentile = stats.norm.cdf(z_score) * 100
        return max(0.1, min(99.9, percentile))  # Medical convention avoids 0/100
    
    def estimate_ga_from_measurement(self, measurement: float, 
                                     metric_type: str) -> float:
        """Estimate GA from measurement using binary search/interpolation match"""
        if metric_type not in self.valid_metrics:
            raise ValueError(f"Invalid metric. Must be one of {self.valid_metrics}")
        
        best_ga = None
        min_diff = float('inf')
        
        # Search from weeks 14 to 42 in small steps
        for ga in np.arange(14, 42.1, 0.1):
            expected = self.get_expected_value(ga, metric_type)
            diff = abs(measurement - expected)
            if diff < min_diff:
                min_diff = diff
                best_ga = ga
        
        return round(float(best_ga), 1) if best_ga else 28.0
    
    def classify_growth(self, percentile: float) -> Dict[str, str]:
        """Classify growth based on standard medical percentiles (3/10/90/97)"""
        if percentile < 3:
            return {'classification': 'SGA', 'full_name': 'Small for Gestational Age', 'severity': 'Severe', 'flag': '⚠️'}
        elif percentile < 10:
            return {'classification': 'SGA', 'full_name': 'Small for Gestational Age', 'severity': 'Mild', 'flag': '⚠️'}
        elif percentile <= 90:
            return {'classification': 'AGA', 'full_name': 'Appropriate for Gestational Age', 'severity': 'Normal', 'flag': '✓'}
        elif percentile <= 97:
            return {'classification': 'LGA', 'full_name': 'Large for Gestational Age', 'severity': 'Mild', 'flag': '⚠️'}
        else:
            return {'classification': 'LGA', 'full_name': 'Large for Gestational Age', 'severity': 'Severe', 'flag': '⚠️'}
    
    def get_expected_range(self, ga_weeks: float, metric_type: str, 
                           percentile_range: Tuple[float, float] = (10, 90)) -> Tuple[float, float]:
        """Get expected value range for GA (default 10th to 90th)"""
        expected = self.get_expected_value(ga_weeks, metric_type)
        sd = self.sd[metric_type]
        
        z_lower = stats.norm.ppf(percentile_range[0] / 100)
        z_upper = stats.norm.ppf(percentile_range[1] / 100)
        
        return (expected + z_lower * sd, expected + z_upper * sd)
    
    def assess_measurement(self, measurement: float, ga_weeks: Optional[float], 
                           metric_type: str) -> Dict:
        """Complete assessment of a single measurement using the active standard"""
        estimated_ga = self.estimate_ga_from_measurement(measurement, metric_type)
        ga_for_calc = ga_weeks if ga_weeks is not None else estimated_ga
        
        percentile = self.calculate_percentile(measurement, ga_for_calc, metric_type)
        z_score = self.calculate_z_score(measurement, ga_for_calc, metric_type)
        growth = self.classify_growth(percentile)
        expected_range = self.get_expected_range(ga_for_calc, metric_type)
        
        return {
            'measurement': measurement,
            'metric_type': metric_type,
            'standard': self.display_name,
            'ga_weeks': ga_for_calc,
            'ga_provided': ga_weeks is not None,
            'estimated_ga': estimated_ga,
            'percentile': round(percentile, 1),
            'z_score': round(z_score, 2),
            'classification': growth['classification'],
            'classification_full': growth['full_name'],
            'severity': growth['severity'],
            'flag': growth['flag'],
            'expected_range': (round(expected_range[0], 1), round(expected_range[1], 1)),
            'within_normal': 10 <= percentile <= 90
        }


# For backward compatibility
def Intergrowth21():
    return FetalGrowthProvider(standard_id='INTERGROWTH')

class MultiStandardConsensus:
    """
    Evaluates fetal measurements against multiple clinical standards simultaneously
    to provide a consensus view and detect clinical discordance.
    """
    
    def __init__(self, standards_to_use=['INTERGROWTH', 'WHO', 'HADLOCK']):
        self.providers = {
            std: FetalGrowthProvider(std) for std in standards_to_use
        }
        self.standards = standards_to_use

    def assess_consensus(self, measurement: float, ga_weeks: float, metric_type: str) -> Dict:
        """Compares a single measurement across all enabled standards"""
        results = {}
        percentiles = []
        classifications = set()
        
        for std_id, provider in self.providers.items():
            if metric_type in provider.valid_metrics:
                assessment = provider.assess_measurement(measurement, ga_weeks, metric_type)
                results[std_id] = {
                    'percentile': assessment['percentile'],
                    'classification': assessment['classification'],
                    'z_score': assessment['z_score'],
                    'expected': assessment['expected_range']
                }
                percentiles.append(assessment['percentile'])
                classifications.add(assessment['classification'])

        if not percentiles:
            return {'error': 'Metric not supported by any standard'}

        # Calculate statistics
        min_p = min(percentiles)
        max_p = max(percentiles)
        median_p = round(np.median(percentiles), 1)
        
        # Clinical Discordance Detection
        # Discordant if one standard says SGA/LGA and another says AGA
        is_discordant = len(classifications) > 1
        
        # Severity of discordance
        severity = "Low"
        if is_discordant:
            if ('SGA' in classifications and 'LGA' in classifications):
                severity = "High" # Extremely rare/impossible with normal data, but good to catch
            elif ('SGA' in classifications or 'LGA' in classifications) and 'AGA' in classifications:
                severity = "Moderate"

        return {
            'metric': metric_type,
            'ga_weeks': ga_weeks,
            'measurement': measurement,
            'standards': results,
            'consensus': {
                'median_percentile': median_p,
                'min_percentile': min_p,
                'max_percentile': max_p,
                'range': round(max_p - min_p, 1),
                'is_discordant': is_discordant,
                'discordance_severity': severity
            }
        }

    def analyze_patient_consensus(self, history_manager, patient_id: str) -> Dict:
        """Analyzes the latest scan of a patient for multi-standard consensus"""
        history = history_manager.get_patient_history(patient_id)
        if not history:
            return {'error': 'No history found for patient'}
            
        latest = history[-1]['data']
        measurements = latest.get('measurements', {})
        ga_weeks = latest.get('clinical', {}).get('estimated_ga')
        
        consensus_report = {}
        for metric, val in measurements.items():
            if metric.upper() in ['HC', 'AC', 'FL', 'BPD']:
                consensus_report[metric] = self.assess_consensus(float(val), ga_weeks, metric.upper())
                
        return {
            'patient_id': patient_id,
            'timestamp': history[-1].get('timestamp'),
            'ga_weeks': ga_weeks,
            'metrics': consensus_report
        }
