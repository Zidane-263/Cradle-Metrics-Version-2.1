"""
Clinical Recommendations Generator
Provides evidence-based recommendations based on risk assessment
"""

from typing import Dict, List
import yaml
import os


class RecommendationGenerator:
    """Generate clinical recommendations based on assessment results"""
    
    def __init__(self, config_path: str = None):
        """Initialize with clinical thresholds configuration"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'clinical_thresholds.yaml')
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.recommendations = self.config['recommendations']
    
    def generate_recommendations(self, assessment: Dict) -> List[Dict]:
        """
        Generate clinical recommendations based on assessment
        
        Args:
            assessment: Clinical assessment from ClinicalRulesEngine
        
        Returns:
            List of recommendation dicts with priority, category, and text
        """
        recommendations = []
        
        # Growth pattern recommendations
        if 'growth_pattern' in assessment and 'pattern' in assessment['growth_pattern']:
            pattern = assessment['growth_pattern']['pattern']
            if pattern in self.recommendations:
                for rec in self.recommendations[pattern]:
                    recommendations.append({
                        'priority': 'high' if pattern in ['IUGR', 'microcephaly'] else 'medium',
                        'category': 'Growth Pattern',
                        'text': rec,
                        'pattern': pattern
                    })
        
        # Borderline measurements recommendations
        borderline_count = sum(
            1 for m in assessment.get('measurements', {}).values()
            if m.get('risk_level') == 'borderline'
        )
        if borderline_count > 0:
            for rec in self.recommendations['borderline_measurements']:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'Monitoring',
                    'text': rec
                })
        
        # Normal case recommendations
        if assessment.get('overall_risk') == 'normal':
            for rec in self.recommendations['normal']:
                recommendations.append({
                    'priority': 'low',
                    'category': 'Routine Care',
                    'text': rec
                })
        
        # Gestational age specific recommendations
        if 'gestational_age' in assessment:
            ga_risk = assessment['gestational_age'].get('risk_level')
            if ga_risk in ['high_risk', 'critical']:
                recommendations.append({
                    'priority': 'high',
                    'category': 'Gestational Age',
                    'text': 'Consult obstetrics for delivery planning'
                })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return recommendations
    
    def generate_follow_up_plan(self, assessment: Dict) -> Dict:
        """Generate follow-up schedule based on risk level"""
        risk_level = assessment.get('overall_risk', 'normal')
        
        follow_up_schedules = {
            'critical': {
                'next_scan': '1 week',
                'frequency': 'Weekly until delivery',
                'specialist': 'Maternal-Fetal Medicine (urgent)',
                'additional': ['Doppler studies', 'Non-stress tests']
            },
            'high_risk': {
                'next_scan': '2 weeks',
                'frequency': 'Every 2 weeks',
                'specialist': 'Maternal-Fetal Medicine',
                'additional': ['Growth velocity tracking', 'Amniotic fluid assessment']
            },
            'borderline': {
                'next_scan': '3-4 weeks',
                'frequency': 'Every 3-4 weeks',
                'specialist': 'Consider specialist consultation',
                'additional': ['Repeat measurements', 'Trend analysis']
            },
            'normal': {
                'next_scan': 'Per routine protocol',
                'frequency': 'Standard prenatal schedule',
                'specialist': 'Not required',
                'additional': ['Continue routine prenatal care']
            }
        }
        
        return follow_up_schedules.get(risk_level, follow_up_schedules['normal'])
    
    def generate_patient_summary(self, assessment: Dict, recommendations: List[Dict]) -> str:
        """
        Generate a professional 'Smart Narrative' summary synthesizing all clinical findings.
        """
        overall_risk = assessment.get('overall_risk', 'normal').replace('_', ' ')
        efw_data = assessment.get('efw', {})
        ci_data = assessment.get('ci', {})
        afi_data = assessment.get('afi', {})
        doppler_data = assessment.get('doppler', {})
        
        # 1. Opening: Growth Status & Weight
        if efw_data and 'value' in efw_data:
            efw_text = f"Estimated Fetal Weight (EFW) is {efw_data['value']}{efw_data['unit']} ({efw_data['percentile']}th percentile)."
        else:
            efw_text = "Fetal biometry is currently being monitored."

        # 2. Growth Pattern & Classification
        pattern_text = ""
        if 'growth_pattern' in assessment:
            pattern = assessment['growth_pattern'].get('pattern', 'AGA')
            if pattern == 'IUGR':
                pattern_text = " Findings are suspicious for Fetal Growth Restriction (FGR)."
            elif pattern == 'macrosomia':
                pattern_text = " Findings suggest accelerated growth (Macrosomia)."
            elif pattern == 'AGA':
                pattern_text = " Growth remains appropriate for gestational age (AGA)."

        # 3. Hegodynamic & Fluid Assessment (The "Integration" part)
        doppler_text = ""
        if doppler_data and 'cpr' in doppler_data:
            cpr = doppler_data['cpr']
            if doppler_data.get('cpr_status') == 'abnormal':
                doppler_text = f" However, Doppler CPR is reduced ({cpr}), suggesting potential brain-sparing physiology."
            else:
                doppler_text = f" Doppler studies show a normal CPR ({cpr}), suggesting stable fetal hemodynamics."

        afi_text = ""
        if afi_data and 'value' in afi_data:
            if afi_data.get('status') != 'normal':
                afi_text = f" Amniotic fluid is {afi_data['classification'].lower()} (AFI: {afi_data['value']}cm)."
            else:
                afi_text = " Amniotic fluid volume is normal."

        # 4. Morphological Indicators
        ci_text = ""
        if ci_data and ci_data.get('status') != 'normal':
            ci_text = f" Head morphology shows {ci_data['status']} ({ci_data['value']}%)."

        # 5. Conclusion/Triage
        conclusion = ""
        if overall_risk == 'critical':
            conclusion = " IMMEDIATE clinical correlation and specialist consultation is advised."
        elif overall_risk == 'high risk':
            conclusion = " Close longitudinal follow-up is recommended to monitor growth velocity."
        else:
            conclusion = " Routine prenatal care is appropriate."

        narrative = f"{efw_text}{pattern_text}{doppler_text}{afi_text}{ci_text}{conclusion}"
        return narrative
    
    def format_for_report(self, assessment: Dict, recommendations: List[Dict]) -> Dict:
        """Format assessment and recommendations for clinical report"""
        return {
            'summary': self.generate_patient_summary(assessment, recommendations),
            'risk_level': assessment.get('overall_risk', 'normal'),
            'recommendations': recommendations,
            'follow_up': self.generate_follow_up_plan(assessment),
            'alerts': assessment.get('alerts', []),
            'clinical_notes': self._generate_clinical_notes(assessment)
        }
    
    def _generate_clinical_notes(self, assessment: Dict) -> List[str]:
        """Generate clinical notes for healthcare providers"""
        notes = []
        
        # Overall assessment
        risk = assessment.get('overall_risk', 'normal')
        notes.append(f"Overall risk assessment: {risk.upper().replace('_', ' ')}")
        
        # Growth pattern
        if 'growth_pattern' in assessment:
            pattern = assessment['growth_pattern'].get('pattern', 'Unknown')
            desc = assessment['growth_pattern'].get('description', '')
            notes.append(f"Growth pattern: {pattern} - {desc}")
        
        # Individual measurements
        for key, result in assessment.get('measurements', {}).items():
            notes.append(f"{key}: {result.get('message', 'No data')}")
        
        # Gestational age
        if 'gestational_age' in assessment:
            notes.append(assessment['gestational_age'].get('message', ''))
        
        return notes


# Example usage
if __name__ == "__main__":
    from clinical_rules import ClinicalRulesEngine
    
    # Initialize
    engine = ClinicalRulesEngine()
    rec_gen = RecommendationGenerator()
    
    # Sample data
    sample_data = {
        'HC': {'value': 245, 'percentile': 50},
        'AC': {'value': 289, 'percentile': 52},
        'BPD': {'value': 75, 'percentile': 48},
        'FL': {'value': 65, 'percentile': 51},
        'GA': {'value': 28.3}
    }
    
    # Generate assessment and recommendations
    assessment = engine.generate_comprehensive_assessment(sample_data)
    recommendations = rec_gen.generate_recommendations(assessment)
    report = rec_gen.format_for_report(assessment, recommendations)
    
    print("Clinical Report:")
    print(f"Summary: {report['summary']}")
    print(f"\nRecommendations ({len(recommendations)}):")
    for rec in recommendations:
        print(f"  [{rec['priority'].upper()}] {rec['text']}")
