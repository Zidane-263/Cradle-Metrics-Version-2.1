#!/usr/bin/env python3
"""
Flask Web Application for Fetal Ultrasound Analysis
Professional medical-grade web interface
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import json
import math
import base64
import tempfile
import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from automatic_pipeline import AutomaticPipeline
from clinical_rules import ClinicalRulesEngine
from recommendations import RecommendationGenerator
from clinical_history import ClinicalHistoryManager
from utils.growth_standards import FetalGrowthProvider, MultiStandardConsensus

# Optional PDF report generator (requires reportlab)
try:
    from report_generator import ClinicalReportGenerator
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️  reportlab not installed. PDF reports disabled. Install with: pip install reportlab pyyaml")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = str(project_root / 'web_app' / 'uploads')
app.config['RESULTS_FOLDER'] = str(project_root / 'web_app' / 'results')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'bmp', 'tif', 'tiff'}

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Initialize pipeline (lazy loading)
pipeline = None
clinical_engine = None
quality_assessor = None
rec_generator = None
report_generator = None
history_manager = None
consensus_engine = None


def get_pipeline():
    """Get or create pipeline instance"""
    global pipeline
    if pipeline is None:
        # Use absolute paths
        yolo_model = str(project_root / 'runs' / 'detect' / 'fetal_detection' / 'weights' / 'best.pt')
        sam_model = str(project_root / 'sam_vit_b_01ec64.pth')
        
        pipeline = AutomaticPipeline(
            yolo_model_path=yolo_model,
            sam_checkpoint=sam_model,
            pixel_to_mm=2.5,
            enable_clinical=True
        )
    return pipeline


def get_clinical_engine():
    """Get or create clinical rules engine"""
    global clinical_engine
    if clinical_engine is None:
        clinical_engine = ClinicalRulesEngine()
    return clinical_engine


def get_rec_generator():
    """Get or create recommendation generator"""
    global rec_generator
    if rec_generator is None:
        rec_generator = RecommendationGenerator()
    return rec_generator

def get_quality_assessor():
    """Get or create quality assessor"""
    global quality_assessor
    if quality_assessor is None:
        from clinical_rules import AnatomicalQualityAssessor
        quality_assessor = AnatomicalQualityAssessor()
    return quality_assessor


def get_report_generator():
    """Get or create PDF report generator"""
    global report_generator
    if not PDF_AVAILABLE:
        return None
    if report_generator is None:
        reports_dir = str(project_root / 'web_app' / 'reports')
        report_generator = ClinicalReportGenerator(output_dir=reports_dir)
    return report_generator


def get_history_manager():
    """Get or create clinical history manager"""
    global history_manager
    if history_manager is None:
        history_manager = ClinicalHistoryManager()
    return history_manager


def get_consensus_engine():
    """Get or create multi-standard consensus engine"""
    global consensus_engine
    if consensus_engine is None:
        consensus_engine = MultiStandardConsensus()
    return consensus_engine


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Landing page"""
    return render_template('landing.html')




@app.route('/analyze')
def analyze():
    """Analysis page"""
    file_id = request.args.get('file_id')
    return render_template('index.html', file_id=file_id)

@app.route('/patients')
def patients_page():
    """Render patient directory page"""
    file_id = request.args.get('file_id')
    return render_template('patients.html', file_id=file_id)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{file_id}.{ext}"
    
    # Save file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    return jsonify({
        'success': True,
        'file_id': file_id,
        'filename': filename
    })


@app.route('/api/process', methods=['POST'])
def process_image():
    """Process uploaded image"""
    
    data = request.get_json(silent=True) or {}
    print(f"🔍 [API Debug] Incoming Process Payload Keys: {list(data.keys())}")
    print(f"🔍 [API Debug] Patient ID in JSON: {data.get('patient_id')}")
    
    file_id = data.get('file_id')
    ga_weeks = data.get('ga_weeks')
    
    # NEW: Advanced Clinical Inputs
    afi = data.get('afi')
    ua_pi = data.get('ua_pi')
    mca_pi = data.get('mca_pi')
    
    if not file_id:
        return jsonify({'error': 'No file_id provided'}), 400
    
    # Find file
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    files = list(upload_folder.glob(f"{file_id}.*"))
    
    if not files:
        return jsonify({'error': 'File not found'}), 404
    
    filepath = files[0]
    
    try:
        # Get pipeline
        pipe = get_pipeline()
        
        # Update GA and Standard if provided
        standard_id = data.get('standard_id', 'INTERGROWTH')
        if ga_weeks:
            pipe.ga_weeks = float(ga_weeks)
        
        if pipe.enable_clinical:
            pipe.clinical_assessor.set_standard(standard_id)
        
        # Initialize clinical variables
        analysis_data = {}
        percentiles = {}
        assessment = {}
        recommendations = []
        
        # NEW: Measure actual execution time
        import time
        start_time = time.time()
        
        # Process image
        results_dir = os.path.join(app.config['RESULTS_FOLDER'], file_id)
        os.makedirs(results_dir, exist_ok=True)
        
        # Save a copy of the original image to the results folder for easy access
        import shutil
        original_copy_path = os.path.join(results_dir, f"original{filepath.suffix}")
        shutil.copy2(filepath, original_copy_path)
        
        results = pipe.process_image(
            str(filepath),
            output_dir=results_dir
        )
        
        # Extract results
        response = {
            'success': True,
            'file_id': file_id,
            'detections': []
        }
        
        # Add detections
        for det in results['detections']:
            response['detections'].append({
                'label': det['label'],
                'confidence': round(det['confidence'], 3)
            })
        
        # Add measurements
        metrics = results['segmentation']['metrics']
        spatial = metrics.get('spatial_metrics', {})
        
        measurements = {}
        if 'head_circumference' in spatial:
            measurements['HC'] = round(spatial['head_circumference'], 1)
        if 'abdomen_circumference' in spatial:
            measurements['AC'] = round(spatial['abdomen_circumference'], 1)
        if 'biparietal_diameter' in spatial:
            measurements['BPD'] = round(spatial['biparietal_diameter'], 1)
        if 'femur_length' in spatial:
            measurements['FL'] = round(spatial['femur_length'], 1)
        
        # Add limb lengths
        if 'limb_lengths' in spatial:
            for limb, length in spatial['limb_lengths'].items():
                label = limb.upper() if len(limb) <= 3 else limb.capitalize()
                measurements[label] = round(length, 1)
        
        # Add geometric/aspect metrics
        if 'head_aspect_ratio' in spatial:
            measurements['head_aspect_ratio'] = spatial['head_aspect_ratio']
        if 'abdomen_aspect_ratio' in spatial:
            measurements['abdomen_aspect_ratio'] = spatial['abdomen_aspect_ratio']
            
        response['measurements'] = measurements
        # Full metrics for 3D reconstruction and internal use
        response['metrics'] = metrics
        response['unit'] = metrics.get('unit', 'mm') # Default to mm for professional view
        
        # Add clinical assessment
        if pipe.enable_clinical and measurements:
            clinical = pipe.clinical_assessor.assess_all_measurements(
                measurements, pipe.ga_weeks
            )
            
            response['clinical'] = {
                'estimated_ga': clinical['consensus_ga'],
                'ga_uncertainty': clinical['ga_uncertainty'],
                'ga_consistency': clinical['ga_consistency'],
                'growth_status': clinical['overall_assessment']['status'],
                'flags': clinical['overall_assessment']['flags']
            }
            
            # Add percentiles
            percentiles = {}
            for metric, data in clinical['measurements'].items():
                percentiles[metric] = {
                    'percentile': round(data['percentile'], 1),
                    'classification': data['classification'],
                    'flag': data['flag']
                }
            response['percentiles'] = percentiles
        
        # Find result image
        result_images = list(Path(results_dir).glob('*_result.png'))
        if result_images:
            response['result_image'] = f"/api/results/{file_id}/{result_images[0].name}"
        
        # Enhanced Clinical Assessment using new rules engine
        if measurements:
            # Prepare data for clinical engine
            analysis_data = {}
            for key, value in measurements.items():
                perc_data = percentiles.get(key, {})
                analysis_data[key] = {
                    'value': value,
                    'percentile': perc_data.get('percentile') if perc_data else None
                }
            
            # Add GA
            if 'clinical' in response:
                analysis_data['GA'] = {'value': response['clinical']['estimated_ga']}
            
            # Add AFI and Doppler to analysis_data
            if afi is not None:
                analysis_data['AFI'] = {'value': float(afi)}
            if ua_pi is not None:
                analysis_data['UA_PI'] = {'value': float(ua_pi)}
            if mca_pi is not None:
                analysis_data['MCA_PI'] = {'value': float(mca_pi)}
            
            # Generate comprehensive assessment
            engine = get_clinical_engine()
            assessment = engine.generate_comprehensive_assessment(analysis_data)
            
            # Generate recommendations
            rec_gen = get_rec_generator()
            recommendations = rec_gen.generate_recommendations(assessment)
            report_data = rec_gen.format_for_report(assessment, recommendations)
            
            # Add to response
            response['risk_assessment'] = {
                'overall_risk': assessment['overall_risk'],
                'risk_color': assessment.get('measurements', {}).get('HC', {}).get('color', '#10b981'),
                'growth_pattern': assessment.get('growth_pattern', {}),
                'alerts': assessment.get('alerts', []),
                'priority': assessment.get('priority', 0),
                'efw': assessment.get('efw'),
                'ci': assessment.get('ci'),
                'afi': assessment.get('afi'),
                'doppler': assessment.get('doppler')
            }
            
            # Anatomical Quality Assessment
            q_assessor = get_quality_assessor()
            q_results = q_assessor.assess_quality(response)
            response['quality_score'] = q_results
            
            response['recommendations'] = recommendations
            response['clinical_summary'] = report_data['summary']
            response['follow_up'] = report_data['follow_up']
            
        # Add actual processing time
        response['processing_time'] = round(time.time() - start_time, 2)
            
        # Growth History & Velocity
        patient_id = data.get('patient_id')
        print(f"🔍 [API Debug] Raw patient_id from payload: \"{patient_id}\"")
        
        # Robust fallback and sanitization
        if patient_id and str(patient_id).strip():
            import re
            patient_id = re.sub(r'[^\w\s-]', '', str(patient_id)).strip().replace(' ', '_')
            if not patient_id:
                patient_id = 'default_patient'
        else:
            # Check if this is a process from the batch analyzer (often doesn't have ID when extraction fails)
            patient_id = 'default_patient'
            print("⚠️ [API Warning] patient_id is missing or empty. Defaulting to 'default_patient'")
            
        print(f"📊 [History Trace] Persisting record for Final Patient ID: \"{patient_id}\"")
        
        # NUCLEAR DEBUG: Write to a persistent file we can definitely read
        try:
            with open('c:/Projects/Zidane/LAST_ID.txt', 'a') as f:
                f.write(f"{datetime.datetime.now().isoformat()} | Raw: {data.get('patient_id')} | Final: {patient_id}\n")
        except Exception as e:
            print(f"⚠️ [API Warning] Failed to write LAST_ID.txt: {e}")
            
        history_mgr = get_history_manager()
        
        # Save this record
        history_mgr.save_record(patient_id, response)
        
        # Calculate and add velocity
        velocity_data = history_mgr.calculate_velocity(patient_id, response)
        if velocity_data:
            response['growth_velocity'] = velocity_data
            
        # Attach quality score and processing time to assessment for report consistency
        assessment['quality_score'] = response.get('quality_score', {})
        assessment['processing_time'] = response.get('processing_time', 0)
        
        # Store assessment for PDF generation
        response['_assessment'] = assessment  # Internal use only
        
        # Save results to JSON for report generation
        with open(os.path.join(results_dir, 'results.json'), 'w') as f:
            json.dump(response, f, default=str)
            
        return jsonify(response)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/results/<file_id>/<filename>')
def get_result(file_id, filename):
    """Serve result images"""
    results_dir = os.path.join(app.config['RESULTS_FOLDER'], file_id)
    return send_from_directory(results_dir, filename)


@app.route('/report/<file_id>')
def report_preview(file_id):
    """Render aesthetic report preview page"""
    results_dir = Path(app.config['RESULTS_FOLDER']) / file_id
    json_path = results_dir / 'results.json'
    
    if not json_path.exists():
        return "Report data not found", 404
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    return render_template('report_preview.html', data=data, file_id=file_id)

@app.route('/api/results/<file_id>')
def get_results_data(file_id):
    """API endpoint to get analysis results as JSON"""
    results_dir = Path(app.config['RESULTS_FOLDER']) / file_id
    json_path = results_dir / 'results.json'
    
    if not json_path.exists():
        return jsonify({'success': False, 'error': 'Results not found'}), 404
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    return jsonify({'success': True, 'data': data})

@app.route('/api/history/<patient_id>')
def get_patient_history(patient_id):
    """API endpoint to get scan history for a patient"""
    # Sanitize incoming patient_id to match saved folder format
    import re
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    
    history_mgr = get_history_manager()
    history = history_mgr.get_patient_history(patient_id)
    return jsonify({
        'success': True,
        'patient_id': patient_id,
        'history': history,
        'count': len(history)
    })


@app.route('/api/patients')
def list_patients():
    """List all patients in history"""
    history_mgr = get_history_manager()
    patients = history_mgr.get_all_patients()
    return jsonify({'patients': patients})



@app.route('/api/consensus/<patient_id>')
def get_consensus_analysis(patient_id):
    """Get multi-standard consensus analysis for a patient's latest scan"""
    import re
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    try:
        history_mgr = get_history_manager()
        engine = get_consensus_engine()
        result = engine.analyze_patient_consensus(history_mgr, patient_id)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 404
            
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/growth_data/<patient_id>/<metric>')
def get_trends(patient_id, metric):
    """Get trend data and reference percentile curves (all 3 standards overlay supported)"""
    import re
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    try:
        standard_id = request.args.get('standard', 'INTERGROWTH')
        overlay_all = request.args.get('overlay_all', 'false').lower() == 'true'
        history_mgr = get_history_manager()
        patient_data = history_mgr.get_trend_data(patient_id, metric)

        # Append current unsaved scan point if provided
        current_ga = request.args.get('current_ga', type=float)
        current_val = request.args.get('current_val', type=float)
        if current_ga is not None and current_val is not None:
            if not any(abs(p['ga'] - current_ga) < 0.1 for p in patient_data):
                patient_data.append({'ga': current_ga, 'value': current_val, 'date': ''})

        from utils.growth_standards import FetalGrowthProvider, MultiStandardConsensus

        def build_reference_curves(std_id):
            calc = FetalGrowthProvider(standard_id=std_id)
            curves = {'10th': [], '50th': [], '90th': []}
            for ga in range(14, 41):
                try:
                    if metric.upper() == 'EFW':
                        mean_ln_efw = 0.578 + (0.332 * ga) - (0.00354 * (ga ** 2))
                        mean_efw = math.exp(mean_ln_efw)
                        sd = mean_efw * 0.15
                        curves['50th'].append({'x': ga, 'y': round(mean_efw, 1)})
                        curves['10th'].append({'x': ga, 'y': round(max(0, mean_efw - 1.28 * sd), 1)})
                        curves['90th'].append({'x': ga, 'y': round(mean_efw + 1.28 * sd, 1)})
                    elif metric.upper() in calc.valid_metrics:
                        expected = calc.get_expected_value(ga, metric.upper())
                        sd = calc.sd[metric.upper()]
                        curves['50th'].append({'x': ga, 'y': round(expected, 1)})
                        curves['10th'].append({'x': ga, 'y': round(max(0, expected - 1.28 * sd), 1)})
                        curves['90th'].append({'x': ga, 'y': round(expected + 1.28 * sd, 1)})
                except:
                    continue
            return curves

        reference_curves = build_reference_curves(standard_id)

        # Optional: all 3 standards overlay
        all_standards = {}
        if overlay_all:
            for std in ['INTERGROWTH', 'WHO', 'HADLOCK']:
                all_standards[std] = build_reference_curves(std)

        # Filter and sort patient data
        def is_valid_point(p):
            try:
                return math.isfinite(float(p.get('value', 0)))
            except (TypeError, ValueError):
                return False

        patient_data = [p for p in patient_data if is_valid_point(p)]
        patient_data.sort(key=lambda x: x['ga'])

        # Compute Z-scores for each patient data point
        z_series = []
        for p in patient_data:
            p_ga = p['ga']
            p_val = p['value']
            mean_pt = next((pt['y'] for pt in reference_curves['50th'] if abs(pt['x'] - p_ga) <= 1), None)
            upper_pt = next((pt['y'] for pt in reference_curves['90th'] if abs(pt['x'] - p_ga) <= 1), None)
            if mean_pt is not None and upper_pt is not None:
                sd_pt = (upper_pt - mean_pt) / 1.28
                if sd_pt > 0:
                    z = round((p_val - mean_pt) / sd_pt, 2)
                    z_series.append({'x': round(p_ga, 1), 'y': z, 'date': p.get('date', '')})

        # Forecast generation
        forecast = []
        if len(patient_data) >= 2:
            x = [p['ga'] for p in patient_data]
            y = [p['value'] for p in patient_data]
            if len(set(x)) >= 2:
                n = len(x)
                sum_x = sum(x); sum_y = sum(y)
                sum_xx = sum(xi * xi for xi in x)
                sum_xy = sum(xi * yi for xi, yi in zip(x, y))
                denom = (n * sum_xx - sum_x * sum_x)
                if denom != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / denom
                    intercept = (sum_y - slope * sum_x) / n
                    last_ga = max(x)
                    for i in range(1, 5):
                        f_ga = last_ga + i
                        if f_ga > 42: break
                        f_val = slope * f_ga + intercept
                        if f_val > 0:
                            forecast.append({'ga': round(f_ga, 1), 'value': round(f_val, 2)})

        elif len(patient_data) == 1:
            pt_ga = patient_data[0]['ga']
            pt_val = patient_data[0]['value']
            mean_pt = next((p['y'] for p in reference_curves['50th'] if abs(p['x'] - pt_ga) <= 0.5), None)
            upper_pt = next((p['y'] for p in reference_curves['90th'] if abs(p['x'] - pt_ga) <= 0.5), None)
            if mean_pt is not None and upper_pt is not None:
                sd_pt = (upper_pt - mean_pt) / 1.28
                if sd_pt > 0:
                    z_score = (pt_val - mean_pt) / sd_pt
                    for i in range(1, 5):
                        f_ga = pt_ga + i
                        if f_ga > 40: break
                        f_mean = next((p['y'] for p in reference_curves['50th'] if abs(p['x'] - f_ga) <= 0.5), None)
                        f_upper = next((p['y'] for p in reference_curves['90th'] if abs(p['x'] - f_ga) <= 0.5), None)
                        if f_mean is not None and f_upper is not None:
                            f_sd = (f_upper - f_mean) / 1.28
                            f_val = f_mean + z_score * f_sd
                            forecast.append({'ga': round(f_ga, 1), 'value': round(f_val, 1)})

        response_data = {
            'patient_data': [{'x': p['ga'], 'y': p['value'], 'date': p.get('date', '')} for p in patient_data],
            'forecast': [{'x': p['ga'], 'y': p['value']} for p in forecast],
            'reference': reference_curves,
            'z_series': z_series,
            'metric': metric,
            'unit': 'g' if metric.upper() == 'EFW' else 'mm'
        }
        if overlay_all:
            response_data['all_standards'] = all_standards

        return jsonify(response_data)

    except Exception as e:
        import traceback
        with open('error.log', 'w') as f:
            f.write(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────
# ADVANCED ANALYTICS ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.route('/api/edd/<patient_id>')
def get_edd(patient_id):
    """Calculate Estimated Delivery Date from latest biometric GA estimate"""
    import re, datetime
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    try:
        history_mgr = get_history_manager()
        history = history_mgr.get_patient_history(patient_id)
        if not history:
            return jsonify({'error': 'No history found'}), 404

        latest = history[-1]['data']
        estimated_ga = latest.get('clinical', {}).get('estimated_ga')
        if not estimated_ga:
            return jsonify({'error': 'No GA estimate in latest scan'}), 400

        scan_date_str = history[-1].get('timestamp', '')
        try:
            scan_date = datetime.datetime.fromisoformat(scan_date_str)
        except:
            scan_date = datetime.datetime.now()

        weeks_remaining = 40.0 - float(estimated_ga)
        edd = scan_date + datetime.timedelta(weeks=weeks_remaining)

        return jsonify({
            'estimated_ga_at_scan': round(float(estimated_ga), 1),
            'scan_date': scan_date.strftime('%Y-%m-%d'),
            'edd': edd.strftime('%Y-%m-%d'),
            'edd_formatted': edd.strftime('%B %d, %Y'),
            'predicted_edd': edd.strftime('%B %d, %Y'), # Sync with JS
            'weeks_remaining': round(weeks_remaining, 1),
            'trimester': '1st' if estimated_ga < 14 else ('2nd' if estimated_ga < 28 else '3rd')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@app.route('/api/birth_weight_prediction/<patient_id>')
def get_birth_weight_prediction(patient_id):
    """Predict birth weight at 40 weeks using current EFW growth trajectory"""
    import re
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    try:
        history_mgr = get_history_manager()
        history = history_mgr.get_patient_history(patient_id)
        if not history:
            return jsonify({'error': 'No history'}), 404

        # Collect EFW data points from history
        efw_points = []
        for record in history:
            data = record.get('data', {})
            ga = data.get('clinical', {}).get('estimated_ga')
            efw = data.get('risk_assessment', {}).get('efw', {})
            efw_val = efw.get('value') if efw else None
            if ga and efw_val:
                efw_points.append((float(ga), float(efw_val)))

        if not efw_points:
            return jsonify({'error': 'Insufficient EFW data'}), 400

        # Project to 40 weeks using linear regression or single-point Z-score
        if len(efw_points) >= 2:
            x = [p[0] for p in efw_points]
            y = [p[1] for p in efw_points]
            n = len(x)
            sum_x = sum(x); sum_y = sum(y)
            sum_xx = sum(xi*xi for xi in x)
            sum_xy = sum(xi*yi for xi, yi in zip(x,y))
            denom = n*sum_xx - sum_x*sum_x
            if denom != 0:
                slope = (n*sum_xy - sum_x*sum_y) / denom
                intercept = (sum_y - slope*sum_x) / n
                predicted_40w = round(slope*40 + intercept)
            else:
                predicted_40w = round(efw_points[-1][1])
        else:
            # Single point: use standard growth rate (~30g/day near term → ~210g/week)
            current_ga, current_efw = efw_points[-1]
            weeks_to_term = max(0, 40 - current_ga)
            growth_rate_per_week = 210 if current_ga >= 28 else 150
            predicted_40w = round(current_efw + weeks_to_term * growth_rate_per_week)

        # Classify predicted weight
        if predicted_40w < 2500:
            category = 'Low Birth Weight'
            color = '#ef4444'
        elif predicted_40w < 4000:
            category = 'Normal Birth Weight'
            color = '#10b981'
        elif predicted_40w < 4500:
            category = 'Macrosomia (Mild)'
            color = '#f59e0b'
        else:
            category = 'Macrosomia (Severe)'
            color = '#ef4444'

        current_ga_latest = efw_points[-1][0]
        current_efw_latest = efw_points[-1][1]

        # Build projection curve from current GA to 40 weeks
        projection_curve = []
        for w in range(int(current_ga_latest), 41):
            if len(efw_points) >= 2:
                projected = round(slope * w + intercept)
            else:
                weeks_ahead = w - current_ga_latest
                projected = round(current_efw_latest + weeks_ahead * growth_rate_per_week)
            if projected > 0:
                projection_curve.append({'x': w, 'y': projected})

        return jsonify({
            'current_efw': current_efw_latest,
            'current_ga': current_ga_latest,
            'predicted_birth_weight_g': predicted_40w,
            'predicted_birth_weight_kg': round(predicted_40w / 1000, 2),
            'category': category,
            'color': color,
            'projection_curve': projection_curve
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/growth_faltering/<patient_id>')
def check_growth_faltering(patient_id):
    """Detect if patient has crossed 2+ percentile bands downward between scans"""
    import re
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    try:
        history_mgr = get_history_manager()
        history = history_mgr.get_patient_history(patient_id)
        if len(history) < 2:
            return jsonify({'faltering': False, 'message': 'Need at least 2 scans to assess', 'alerts': []})

        from utils.growth_standards import FetalGrowthProvider, MultiStandardConsensus
        calc = FetalGrowthProvider(standard_id='INTERGROWTH')

        def get_percentile_from_value(ga, metric, value):
            try:
                if metric.upper() in calc.valid_metrics:
                    expected = calc.get_expected_value(ga, metric.upper())
                    sd = calc.sd[metric.upper()]
                    z = (value - expected) / sd
                    # Approximate percentile from Z
                    import math
                    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
                    return round(cdf * 100, 1)
            except:
                pass
            return None

        PERCENTILE_BANDS = [3, 10, 25, 50, 75, 90, 97]

        def get_band_index(percentile):
            for i, threshold in enumerate(PERCENTILE_BANDS):
                if percentile <= threshold:
                    return i
            return len(PERCENTILE_BANDS)

        alerts = []
        metrics_to_check = ['HC', 'AC', 'BPD', 'FL']

        for metric in metrics_to_check:
            trend = history_mgr.get_trend_data(patient_id, metric)
            if len(trend) < 2:
                continue

            first = trend[0]
            last = trend[-1]

            p_first = get_percentile_from_value(first['ga'], metric, first['value'])
            p_last = get_percentile_from_value(last['ga'], metric, last['value'])

            if p_first is not None and p_last is not None:
                band_drop = get_band_index(p_first) - get_band_index(p_last)
                if band_drop >= 2:
                    alerts.append({
                        'metric': metric,
                        'from_percentile': p_first,
                        'to_percentile': p_last,
                        'bands_dropped': band_drop,
                        'from_ga': first['ga'],
                        'to_ga': last['ga'],
                        'severity': 'high' if band_drop >= 3 else 'moderate'
                    })

        return jsonify({
            'faltering': len(alerts) > 0,
            'alerts': alerts,
            'scans_analysed': len(history),
            'message': f'{len(alerts)} metric(s) show growth faltering' if alerts else 'No growth faltering detected'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ga_consensus/<patient_id>')
def get_ga_consensus(patient_id):
    """Return individual GA estimates per metric for comparison display"""
    import re
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    try:
        history_mgr = get_history_manager()
        history = history_mgr.get_patient_history(patient_id)
        if not history:
            return jsonify({'error': 'No history'}), 404

        latest = history[-1]['data']
        clinical = latest.get('clinical', {})
        consensus_ga = clinical.get('estimated_ga')

        # Attempt to extract per-metric GA estimates from saved clinical data
        measurements = latest.get('measurements', {})
        percentiles_data = latest.get('percentiles', {})

        from utils.growth_standards import FetalGrowthProvider, MultiStandardConsensus
        calc = FetalGrowthProvider(standard_id='INTERGROWTH')

        per_metric = {}
        for metric in ['HC', 'AC', 'BPD', 'FL']:
            val = measurements.get(metric)
            if val is not None:
                try:
                    estimated = calc.estimate_ga_from_measurement(metric.upper(), float(val))
                    perc = percentiles_data.get(metric, {}).get('percentile')
                    per_metric[metric] = {
                        'estimated_ga': round(float(estimated), 1) if estimated else None,
                        'value': val,
                        'percentile': perc
                    }
                except:
                    per_metric[metric] = {'estimated_ga': None, 'value': val}

        # Compute variance and standard deviation
        ga_values = [v['estimated_ga'] for v in per_metric.values() if v.get('estimated_ga') is not None]
        std_dev = 0
        if len(ga_values) >= 2:
            import math
            mean_ga = sum(ga_values) / len(ga_values)
            variance = sum((g - mean_ga) ** 2 for g in ga_values) / len(ga_values)
            std_dev = math.sqrt(variance)
            consistency = 'Excellent' if variance < 1 else ('Good' if variance < 4 else 'Fair')
        elif len(ga_values) == 1:
            consistency = 'Confidence Base'
        else:
            consistency = 'N/A'

        return jsonify({
            'consensus_ga': round(float(consensus_ga), 1) if consensus_ga else None,
            'per_metric': per_metric,
            'consistency': consistency,
            'std_dev': round(std_dev, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/next_scan_recommendation/<patient_id>')
def get_next_scan_recommendation(patient_id):
    """Recommend next scan timing based on risk level and growth pattern"""
    import re
    patient_id = re.sub(r'[^\w\s-]', '', patient_id).strip().replace(' ', '_')
    try:
        history_mgr = get_history_manager()
        history = history_mgr.get_patient_history(patient_id)
        if not history:
            return jsonify({'error': 'No history'}), 404

        latest = history[-1]['data']
        risk = latest.get('risk_assessment', {})
        clinical = latest.get('clinical', {})

        overall_risk = risk.get('overall_risk', 'normal')
        growth_pattern = risk.get('growth_pattern', {}).get('pattern', 'AGA')
        alerts = risk.get('alerts', [])
        estimated_ga = clinical.get('estimated_ga', 28)

        # Decision logic
        if overall_risk == 'critical' or any('HIGH PRIORITY' in a for a in alerts):
            interval_weeks = 1
            urgency = 'urgent'
            urgency_color = '#ef4444'
            reason = 'Critical risk findings detected. Urgent specialist review required.'
        elif overall_risk == 'high_risk' or growth_pattern == 'IUGR':
            interval_weeks = 1
            urgency = 'urgent'
            urgency_color = '#ef4444'
            reason = 'High risk / growth restriction detected. Weekly monitoring recommended.'
        elif overall_risk == 'borderline' or growth_pattern == 'macrosomia':
            interval_weeks = 2
            urgency = 'soon'
            urgency_color = '#f59e0b'
            reason = 'Borderline findings. Repeat scan in 2 weeks to track trend.'
        elif estimated_ga >= 36:
            interval_weeks = 1
            urgency = 'routine_late'
            urgency_color = '#06b6d4'
            reason = 'Late third trimester — weekly monitoring is standard practice.'
        elif estimated_ga >= 28:
            interval_weeks = 2
            urgency = 'routine'
            urgency_color = '#10b981'
            reason = 'Normal growth in third trimester. Biweekly scan recommended.'
        else:
            interval_weeks = 4
            urgency = 'routine'
            urgency_color = '#10b981'
            reason = 'Normal growth. Routine 4-week interval recommended.'

        import datetime
        scan_date_str = history[-1].get('timestamp', '')
        try:
            scan_date = datetime.datetime.fromisoformat(scan_date_str)
        except:
            scan_date = datetime.datetime.now()

        next_scan_date = scan_date + datetime.timedelta(weeks=interval_weeks)
        today = datetime.datetime.now()
        days_until = (next_scan_date - today).days

        return jsonify({
            'interval_weeks': interval_weeks,
            'next_scan_date': next_scan_date.strftime('%Y-%m-%d'),
            'next_scan_formatted': next_scan_date.strftime('%B %d, %Y'),
            'days_until_next_scan': max(0, days_until),
            'urgency': urgency,
            'urgency_color': urgency_color,
            'reason': reason,
            'overall_risk': overall_risk,
            'growth_pattern': growth_pattern
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/report_with_chart/<file_id>', methods=['POST'])
def generate_report_with_chart(file_id):
    """Generate professional PDF report including a growth chart image"""
    results_dir = Path(app.config['RESULTS_FOLDER']) / file_id
    json_path = results_dir / 'results.json'
    
    if not json_path.exists():
        return jsonify({'error': 'Results not found'}), 404
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    chart_image_b64 = request.json.get('chart_image')
    temp_img_path = None
    
    if chart_image_b64:
        try:
            if ',' in chart_image_b64:
                chart_image_b64 = chart_image_b64.split(',')[1]
            
            # Remove any potential URL encoding
            if '%' in chart_image_b64:
                import urllib.parse
                chart_image_b64 = urllib.parse.unquote(chart_image_b64)
            
            img_data = base64.b64decode(chart_image_b64)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(img_data)
                temp_img_path = tmp.name

            # Optional: verify with PIL
            from PIL import Image
            import io
            try:
                Image.open(io.BytesIO(img_data)).verify()
            except Exception as pic_err:
                raise ValueError(f"Invalid chart image data: {str(pic_err)}")
        except Exception as e:
            print(f"⚠️ Chart image processing error: {e}")
            return jsonify({'error': f"Chart image processing failed: {str(e)}"}), 500

    try:
        if PDF_AVAILABLE:
            report_gen = ClinicalReportGenerator(output_dir=os.path.join(app.root_path, 'reports'))
            if report_gen:
                measurements = data.get('measurements', {})
                percentiles = data.get('percentiles', {})
                analysis_data = {}
                for key, val in measurements.items():
                    perc_val = percentiles.get(key, {})
                    p_score = perc_val.get('percentile') if isinstance(perc_val, dict) else None
                    analysis_data[key] = {'value': val, 'percentile': p_score}
                
                clinical = data.get('clinical', {})
                if 'estimated_ga' in clinical:
                    analysis_data['GA'] = {'value': clinical['estimated_ga']}
                analysis_data['processing_time'] = data.get('processing_time', '---')
                
                assessment = data.get('_assessment', {})
                if 'quality_score' in data and 'quality_score' not in assessment:
                    assessment['quality_score'] = data['quality_score']
                
                recommendations = data.get('recommendations', [])
                
                pdf_path = report_gen.generate_report(
                    analysis_data, assessment, recommendations,
                    chart_image_path=temp_img_path,
                    output_filename=f"CradleMetrics_Report_Advanced_{file_id}.pdf"
                )
                
                @after_this_request
                def cleanup(response):
                    if temp_img_path and os.path.exists(temp_img_path):
                        try: os.remove(temp_img_path)
                        except: pass
                    return response

                download = request.args.get('download', '0') == '1'
                return send_from_directory(
                    os.path.abspath(os.path.dirname(pdf_path)), 
                    os.path.basename(pdf_path),
                    as_attachment=download,
                    mimetype='application/pdf'
                )
    except Exception as e:
        print(f"⚠️ PDF generation failed: {str(e)}")
        if temp_img_path and os.path.exists(temp_img_path):
            try: os.remove(temp_img_path)
            except: pass
        return jsonify({'error': f"PDF generation failed: {str(e)}"}), 500

    return jsonify({'error': 'PDF generation not available'}), 500


@app.route('/api/report/<file_id>')
def generate_report(file_id):
    """Generate and serve clinical report (PDF preferred, CSV fallback)"""
    results_dir = Path(app.config['RESULTS_FOLDER']) / file_id
    json_path = results_dir / 'results.json'
    
    if not json_path.exists():
        return jsonify({'error': 'Results not found'}), 404
        
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Try PDF generation first
    if PDF_AVAILABLE:
        try:
            report_gen = ClinicalReportGenerator(output_dir=os.path.join(app.root_path, 'reports'))
            if report_gen:
                # Prepare data for PDF generator
                # Reconstruct analysis_data to match what report_generator expects
                measurements = data.get('measurements', {})
                percentiles = data.get('percentiles', {})
                analysis_data = {}
                
                for key, value in measurements.items():
                    perc_data = percentiles.get(key, {})
                    p_score = perc_data.get('percentile') if isinstance(perc_data, dict) else None
                    analysis_data[key] = {
                        'value': value,
                        'percentile': p_score
                    }
                
                # Add GA if present
                clinical = data.get('clinical', {})
                if 'estimated_ga' in clinical:
                    analysis_data['GA'] = {'value': clinical['estimated_ga']}

                # Add processing time to analysis_data for PDF
                analysis_data['processing_time'] = data.get('processing_time', '---')

                assessment = data.get('_assessment', {})
                # Ensure quality_score is present in assessment if it exists at top level
                if 'quality_score' in data and 'quality_score' not in assessment:
                    assessment['quality_score'] = data['quality_score']
                
                recommendations = data.get('recommendations', [])
                
                # Generate PDF
                pdf_path = report_gen.generate_report(
                    analysis_data, 
                    assessment, 
                    recommendations,
                    output_filename=f"CradleMetrics_Report_{file_id}.pdf"
                )
                
                download = request.args.get('download', '0') == '1'
                return send_from_directory(
                    os.path.abspath(os.path.dirname(pdf_path)), 
                    os.path.basename(pdf_path),
                    as_attachment=download,
                    mimetype='application/pdf'
                )
        except Exception as e:
            import traceback
            print(f"⚠️ PDF generation failed: {str(e)}\n{traceback.format_exc()}. Falling back to CSV.")
    
    # Fallback to CSV
    import csv
    import io
    from flask import make_response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # ... rest of the existing CSV generation logic ...
    writer.writerow(['Fetal Ultrasound Clinical Report'])
    writer.writerow(['ID', file_id])
    writer.writerow([])
    writer.writerow(['Biometric Measurements'])
    writer.writerow(['Parameter', 'Value', 'Unit', 'Percentile', 'Classification'])
    
    measurements = data.get('measurements', {})
    percentiles = data.get('percentiles', {})
    unit = data.get('unit', 'mm')
    
    for key, value in measurements.items():
        perc = percentiles.get(key, {})
        writer.writerow([
            key, 
            value, 
            unit, 
            perc.get('percentile', 'N/A'), 
            perc.get('classification', 'N/A')
        ])
    
    writer.writerow([])
    writer.writerow(['Clinical Assessment'])
    clinical = data.get('clinical', {})
    writer.writerow(['Estimated GA', f"{clinical.get('estimated_ga', 'N/A')} weeks"])
    writer.writerow(['GA Consistency', clinical.get('ga_consistency', 'N/A')])
    writer.writerow(['Growth Status', clinical.get('growth_status', 'N/A')])
    
    if 'risk_assessment' in data:
        writer.writerow([])
        writer.writerow(['Risk Assessment'])
        risk = data['risk_assessment']
        writer.writerow(['Overall Risk Level', risk.get('overall_risk', 'N/A').upper().replace('_', ' ')])
        writer.writerow(['Growth Pattern', risk.get('growth_pattern', {}).get('pattern', 'N/A')])
        writer.writerow(['Priority', risk.get('priority', 0)])
        
        if risk.get('efw'):
            efw = risk['efw']
            writer.writerow(['Estimated Fetal Weight', f"{efw.get('value')} {efw.get('unit')}", f"{efw.get('percentile', 'N/A')}%"])
        if risk.get('ci'):
            ci = risk['ci']
            writer.writerow(['Cephalic Index', f"{ci.get('value')} {ci.get('unit')}", ci.get('status', 'N/A')])
        if risk.get('afi'):
            afi = risk['afi']
            writer.writerow(['Amniotic Fluid Index', f"{afi.get('value')} {afi.get('unit')}", afi.get('classification', 'N/A')])
        if risk.get('doppler'):
            doppler = risk['doppler']
            writer.writerow(['Doppler (CPR)', doppler.get('cpr', 'N/A'), doppler.get('classification', 'N/A')])
            writer.writerow(['UA-PI', doppler.get('ua_pi', 'N/A')])
            writer.writerow(['MCA-PI', doppler.get('mca_pi', 'N/A')])
            
    # Anatomical Intelligence & Performance
    writer.writerow([])
    writer.writerow(['System Intelligence & Performance'])
    q = data.get('quality_score', {})
    writer.writerow(['Anatomical Quality Score', f"{q.get('score', 'N/A')}/100", q.get('status', 'N/A')])
    writer.writerow(['Plane Accuracy Score', q.get('plane_accuracy', 'N/A')])
    writer.writerow(['AI Confidence Score', q.get('avg_confidence', 'N/A')])
    writer.writerow(['Processing Speed', f"{data.get('processing_time', 'N/A')}s"])
            
    if 'clinical_summary' in data:
        writer.writerow([])
        writer.writerow(['Clinical Summary'])
        writer.writerow([data['clinical_summary']])
    
    if 'recommendations' in data and data['recommendations']:
        writer.writerow([])
        writer.writerow(['Clinical Recommendations'])
        writer.writerow(['Priority', 'Category', 'Recommendation'])
        for rec in data['recommendations']:
            writer.writerow([
                rec.get('priority', 'N/A').upper(),
                rec.get('category', 'N/A'),
                rec.get('text', 'N/A')
            ])
    
    if 'follow_up' in data:
        writer.writerow([])
        writer.writerow(['Follow-up Plan'])
        follow_up = data['follow_up']
        writer.writerow(['Next Scan', follow_up.get('next_scan', 'N/A')])
        writer.writerow(['Frequency', follow_up.get('frequency', 'N/A')])
        writer.writerow(['Specialist', follow_up.get('specialist', 'N/A')])
        if 'additional' in follow_up:
            writer.writerow(['Additional Tests', ', '.join(follow_up['additional'])])
    
    if clinical.get('flags'):
        writer.writerow([])
        writer.writerow(['Clinical Flags'])
        for flag in clinical['flags']:
            writer.writerow([flag])
            
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=CradleMetrics_Report_{file_id}.csv"
    response.headers["Content-type"] = "text/csv"
    return response




@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    print("="*70)
    print("🏥 Fetal Ultrasound Analysis - Web Interface")
    print("="*70)
    print("\n🌐 Starting server...")
    print("📍 Open your browser and go to: http://localhost:8080")
    print("\n⚠️  Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
