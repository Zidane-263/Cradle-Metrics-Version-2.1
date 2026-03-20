#!/usr/bin/env python3
"""
Clinical Assessment Module
Provides comprehensive fetal growth assessment using INTERGROWTH-21st standards
"""

from typing import Dict, List, Optional
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.growth_standards import FetalGrowthProvider


class ClinicalAssessment:
    """
    Comprehensive clinical assessment of fetal biometrics
    """
    
    def __init__(self, standard_id: str = 'INTERGROWTH'):
        """
        Initialize clinical assessment
        
        Args:
            standard_id: Growth standard to use ('INTERGROWTH', 'WHO', 'HADLOCK')
        """
        self.standard_id = standard_id
        self.growth_provider = FetalGrowthProvider(standard_id=standard_id)
    
    def set_standard(self, standard_id: str):
        """Update the growth standard"""
        if standard_id != self.standard_id:
            self.standard_id = standard_id
            self.growth_provider = FetalGrowthProvider(standard_id=standard_id)
    
    def assess_all_measurements(self, measurements: Dict[str, float], 
                               ga_weeks: Optional[float] = None) -> Dict:
        """
        Assess all available biometric measurements
        
        Args:
            measurements: Dict of {'HC': value, 'AC': value, 'FL': value, 'BPD': value}
            ga_weeks: Known gestational age (optional)
        
        Returns:
            Complete clinical assessment
        """
        results = {}
        ga_estimates = []
        
        # Assess each measurement
        for metric, value in measurements.items():
            if value is not None and metric in self.growth_provider.valid_metrics:
                assessment = self.growth_provider.assess_measurement(value, ga_weeks, metric)
                results[metric] = assessment
                ga_estimates.append(assessment['estimated_ga'])
        
        # Calculate consensus GA
        if ga_estimates:
            consensus_ga = np.mean(ga_estimates)
            ga_std = np.std(ga_estimates)
            ga_consistency = "Good" if ga_std < 1.0 else "Variable"
        else:
            consensus_ga = None
            ga_std = None
            ga_consistency = "Unknown"
        
        # Overall assessment
        overall = self._generate_overall_assessment(results, consensus_ga, ga_consistency)
        
        return {
            'measurements': results,
            'consensus_ga': round(consensus_ga, 1) if consensus_ga else None,
            'ga_uncertainty': round(ga_std, 1) if ga_std else None,
            'ga_consistency': ga_consistency,
            'overall_assessment': overall
        }
    
    def _generate_overall_assessment(self, results: Dict, consensus_ga: float, 
                                    consistency: str) -> Dict:
        """Generate overall clinical assessment"""
        
        # Count classifications
        classifications = [r['classification'] for r in results.values()]
        flags = []
        
        # Check for growth issues
        sga_count = classifications.count('SGA')
        lga_count = classifications.count('LGA')
        aga_count = classifications.count('AGA')
        
        # Determine overall status
        if sga_count >= 2:
            status = "Growth Restriction Concern"
            severity = "Warning"
            flags.append("⚠️ Multiple measurements below 10th percentile")
        elif lga_count >= 2:
            status = "Macrosomia Concern"
            severity = "Warning"
            flags.append("⚠️ Multiple measurements above 90th percentile")
        elif aga_count == len(classifications):
            status = "Normal Fetal Growth"
            severity = "Normal"
            flags.append("✓ All measurements within normal range")
        else:
            status = "Mixed Growth Pattern"
            severity = "Review"
            flags.append("ℹ️ Measurements show variable growth pattern")
        
        # Check consistency
        if consistency == "Variable":
            flags.append("⚠️ Measurements suggest different gestational ages")
        
        return {
            'status': status,
            'severity': severity,
            'flags': flags,
            'sga_count': sga_count,
            'lga_count': lga_count,
            'aga_count': aga_count
        }
    
    def format_clinical_report(self, assessment: Dict) -> str:
        """
        Format assessment as clinical report
        
        Args:
            assessment: Output from assess_all_measurements
        
        Returns:
            Formatted clinical report string
        """
        report = []
        report.append("="*70)
        report.append(f"CLINICAL ASSESSMENT - {self.growth_provider.standard_name}")
        report.append("="*70)
        
        # Measurements
        report.append("\nBiometric Measurements:")
        for metric, data in assessment['measurements'].items():
            flag = data['flag']
            percentile = data['percentile']
            est_ga = data['estimated_ga']
            classification = data['classification']
            
            report.append(
                f"  {metric}: {data['measurement']:.1f}mm "
                f"({percentile:.0f}th %ile, ~{est_ga:.0f}w, {data['standard']}) "
                f"{classification} {flag}"
            )
        
        # Gestational Age
        report.append("\n" + "="*70)
        report.append("Gestational Age Assessment:")
        if assessment['consensus_ga']:
            report.append(
                f"  Estimated GA: {assessment['consensus_ga']:.1f} weeks "
                f"± {assessment['ga_uncertainty']:.1f} weeks"
            )
            report.append(f"  Consistency: {assessment['ga_consistency']}")
        
        # Overall Assessment
        report.append("\n" + "="*70)
        report.append("Overall Assessment:")
        overall = assessment['overall_assessment']
        report.append(f"  Status: {overall['status']}")
        report.append(f"  Severity: {overall['severity']}")
        
        report.append("\nClinical Flags:")
        for flag in overall['flags']:
            report.append(f"  {flag}")
        
        report.append("\n" + "="*70)
        
        return "\n".join(report)


def example_usage():
    """Example usage"""
    
    assessor = ClinicalAssessment()
    
    # Example measurements
    measurements = {
        'HC': 245.3,
        'AC': 289.7,
        'BPD': 85.2,
        'FL': 65.4
    }
    
    # Assess
    assessment = assessor.assess_all_measurements(measurements, ga_weeks=28)
    
    # Print report
    report = assessor.format_clinical_report(assessment)
    print(report)


if __name__ == "__main__":
    example_usage()
