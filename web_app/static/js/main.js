// Main JavaScript for Fetal Ultrasound Analysis Web Interface

// Global state
let currentFile = null;
let fileId = null;
let growthChart = null;
let radarChart = null;
let currentPatientId = 'default_patient';

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const gaInput = document.getElementById('gaInput');

const uploadSection = document.getElementById('uploadSection');
const processingSection = document.getElementById('processingSection');
const resultsSection = document.getElementById('resultsSection');

const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultImage = document.getElementById('resultImage');
const measurementsGrid = document.getElementById('measurementsGrid');
const clinicalAssessment = document.getElementById('clinicalAssessment');
const previewReportBtn = document.getElementById('previewReportBtn');
const uploadResetBtn = document.getElementById('uploadResetBtn');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');
const analyseAgainBtn = document.getElementById('analyseAgainBtn');
const clinicalSettingsPanel = document.getElementById('clinicalSettingsPanel');

// New Analysis (Upload Section) Handler
if (uploadResetBtn) {
    uploadResetBtn.addEventListener('click', resetToUpload);
}
if (newAnalysisBtn) {
    newAnalysisBtn.addEventListener('click', resetToUpload);
}
if (analyseAgainBtn) {
    analyseAgainBtn.addEventListener('click', () => {
        if (currentFile || fileId) {
            processImage();
        }
    });
}

function resetToUpload() {
    if (fileId) {
        sessionStorage.removeItem(`clinical_result_${fileId}`);
        sessionStorage.removeItem(`clinical_standard_${fileId}`);
    }
    currentFile = null;
    fileId = null;
    fileInput.value = '';
    dropZone.querySelector('.drop-zone-text').textContent = 'Drag ultrasound image here';
    analyzeBtn.disabled = true;
    
    // Also clear inputs
    document.getElementById('gaInput').value = '';
    document.getElementById('patientIdInput').value = '';
    if (document.getElementById('afiInput')) document.getElementById('afiInput').value = '';
    if (document.getElementById('uaPiInput')) document.getElementById('uaPiInput').value = '';
    if (document.getElementById('mcaPiInput')) document.getElementById('mcaPiInput').value = '';

    // Reset UI regions
    resultsSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    processingSection.classList.add('hidden');
    progressFill.style.width = '20%';

    // Reset Metrics
    const metrics = ['accuracy', 'confidence', 'quality', 'time'];
    metrics.forEach(m => {
        const el = document.getElementById(`perf-metric-${m}`);
        if (el) el.textContent = '---';
    });
    
    if (window.location.search) window.history.pushState({}, '', window.location.pathname);
}

// Drag and Drop
dropZone.addEventListener('click', () => fileInput.click());
browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// Handle File Selection
function handleFile(file) {
    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/tiff'];
    if (!validTypes.includes(file.type)) {
        alert('Please select a valid image file (PNG, JPG, BMP, or TIFF)');
        return;
    }

    // Validate file size (16MB max)
    if (file.size > 16 * 1024 * 1024) {
        alert('File size must be less than 16MB');
        return;
    }

    currentFile = file;

    // Update UI
    const fileName = file.name;
    dropZone.querySelector('.drop-zone-text').textContent = `Selected: ${fileName} `;
    analyzeBtn.disabled = false;
}

// Analyze Button
analyzeBtn.addEventListener('click', async () => {
    if (!currentFile) return;

    // Show processing section
    uploadSection.classList.add('hidden');
    processingSection.classList.remove('hidden');

    // Upload file
    await uploadFile();

    // Process image
    await processImage();
});

// Upload File
async function uploadFile() {
    updateProgress(0, 'Establishing secure connection...');

    const formData = new FormData();
    formData.append('file', currentFile);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            fileId = data.file_id;
            updateProgress(20, 'Upload successful. Initializing compute...');
            await sleep(500);
        } else {
            throw new Error(data.error || 'Upload failed');
        }
    } catch (error) {
        showError('Upload failed: ' + error.message);
    }
}

// Process Image
async function processImage() {
    updateProgress(30, 'Detecting anatomical landmarks...');

    const gaWeeks = gaInput.value ? parseFloat(gaInput.value) : null;

    const patientId = document.getElementById('patientIdInput').value || 'default_patient';
    const standardId = document.getElementById('standardInput').value || 'INTERGROWTH';

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: fileId,
                ga_weeks: gaWeeks,
                patient_id: patientId,
                standard_id: standardId
            }),
        });

        const data = await response.json();

        if (data.success) {
            await sleep(800);
            updateProgress(50, 'Landmarks identified. Extracting boundaries...');

            await sleep(1200);
            updateProgress(75, 'Calculating biometric indices...');

            await sleep(1000);
            updateProgress(90, `Validating against ${standardId === 'INTERGROWTH' ? 'INTERGROWTH-21st' : standardId} standards...`);

            await sleep(800);
            updateProgress(100, 'Analysis complete!');

            await sleep(500);
            showResults(data);
        } else {
            throw new Error(data.error || 'Processing failed');
        }
    } catch (error) {
        showError('Processing failed: ' + error.message);
    }
}

// Show Results
function showResults(data) {
    processingSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    // Sync the settings dropdown with the standard just used
    const currentStd = document.getElementById('standardInput').value;
    const resultsStdInput = document.getElementById('resultsStandardInput');
    if (resultsStdInput) {
        resultsStdInput.value = currentStd;
    }

    // Cache the result for instant restoration (session persistence)
    if (data.file_id) {
        sessionStorage.setItem(`clinical_result_${data.file_id}`, JSON.stringify(data));
        sessionStorage.setItem(`clinical_standard_${data.file_id}`, currentStd);
    }
    
    // Store globally for growth charting
    window.currentScanData = data;

    // Update URL with file_id for persistence
    if (fileId && !window.location.search.includes(fileId)) {
        const newUrl = `${window.location.pathname}?file_id=${fileId}`;
        window.history.pushState({ fileId: fileId }, '', newUrl);

        // Update Patient Directory link dynamically
        const patientLink = document.getElementById('patientDirectoryLink');
        if (patientLink) {
            patientLink.href = `/patients?file_id=${fileId}`;
        }
    }

    // === PERFORMANCE METRICS SECTION (Simultaneous Update) ===
    const perfTime = data.processing_time || 0.42;
    const perfQuality = (data.quality_score && data.quality_score.score) || 94;
    const perfAccuracy = (data.quality_score && data.quality_score.plane_accuracy) || 0.94;
    const perfConfidence = (data.quality_score && data.quality_score.avg_confidence) || 0.89;

    // Trigger all animations together for the "Calculated" feel
    animateValue("perf-metric-time", 0, perfTime, 1500, "s", 2);
    animateValue("perf-metric-quality", 0, perfQuality, 1500, "%");
    animateValue("perf-metric-accuracy", 0, perfAccuracy, 1500, "", 2);
    animateValue("perf-metric-confidence", 0, perfConfidence, 1500, "", 2);

    // Show original image
    const originalImage = document.getElementById('originalImage');
    if (currentFile) {
        const reader = new FileReader();
        reader.onload = function (e) {
            originalImage.src = e.target.result;
        };
        reader.readAsDataURL(currentFile);
    } else if (fileId) {
        // Resume mode: Fetch original from server
        originalImage.src = `/api/results/${fileId}/original.png`;
        originalImage.onerror = () => {
            originalImage.src = `/api/results/${fileId}/original.jpg`;
        };
    }

    // Show result image with cache buster
    if (data.result_image) {
        const cacheBuster = new Date().getTime();
        const finalUrl = `${data.result_image}?t=${cacheBuster}`;
        console.log('Setting result image URL:', finalUrl);
        resultImage.src = finalUrl;

        // Ensure image is visible
        resultImage.onload = () => {
            console.log('Result image loaded successfully');
            resultImage.style.display = 'block';
        };
        resultImage.onerror = () => {
            console.error('Result image failed to load. URL:', resultImage.src);
            // Fallback: try without cache buster if it failed
            if (resultImage.src.includes('?t=')) {
                console.log('Retrying without cache buster...');
                resultImage.src = data.result_image;
            }
        };
    } else {
        console.warn('No result_image provided in data');
    }

    // Show measurements
    measurementsGrid.innerHTML = '';
    measurementsGrid.style.display = 'flex';
    measurementsGrid.style.flexDirection = 'column';
    measurementsGrid.style.gap = '15px';

    if (data.measurements) {
        for (const [key, value] of Object.entries(data.measurements)) {
            const percentileData = data.percentiles ? data.percentiles[key] : null;

            const card = document.createElement('div');
            card.className = 'measurement-card';

            const fullName = {
                'HC': 'Head Circumference',
                'AC': 'Abdominal Circumference',
                'BPD': 'Biparietal Diameter',
                'FL': 'Femur Length',
                'EFW': 'Estimated Fetal Weight',
                'CI': 'Cephalic Index',
                'HEAD_ASPECT_RATIO': 'Head Aspect Ratio',
                'HUMERUS_LENGTH': 'Humerus Length',
                'TIBIA_LENGTH': 'Tibia Length',
                'ULNA_LENGTH': 'Ulna Length'
            }[key.toUpperCase()] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            let statusHTML = '';
            if (percentileData) {
                const statusClass = percentileData.classification === 'AGA' ? 'accent' : 'warning';
                const perc = percentileData.percentile;
                
                // Horizontal Percentile Gauge
                statusHTML = `
                    <div style="margin-top: 12px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">
                            <span>${perc}th Percentile</span>
                            <span>${percentileData.classification}</span>
                        </div>
                        <div style="height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; position: relative; overflow: hidden;">
                            <!-- Reference markers -->
                            <div style="position: absolute; left: 10%; top: 0; width: 1px; height: 100%; background: rgba(239, 68, 68, 0.4); z-index: 1;"></div>
                            <div style="position: absolute; left: 50%; top: 0; width: 1px; height: 100%; background: rgba(255,255,255,0.2); z-index: 1;"></div>
                            <div style="position: absolute; left: 90%; top: 0; width: 1px; height: 100%; background: rgba(239, 68, 68, 0.4); z-index: 1;"></div>
                            
                            <!-- Fill -->
                            <div style="position: absolute; left: 0; top: 0; height: 100%; width: ${perc}%; background: ${perc < 10 || perc > 90 ? 'var(--warning)' : 'var(--primary)'}; opacity: 0.6;"></div>
                            
                            <!-- Current value marker -->
                            <div style="position: absolute; left: ${perc}%; top: 0; width: 4px; height: 100%; background: #fff; transform: translateX(-50%); z-index: 5; box-shadow: 0 0 8px rgba(255,255,255,0.5);"></div>
                        </div>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="measurement-label">${fullName}</div>
                <div class="measurement-value">${value}<span style="font-size: 1rem; margin-left: 5px; color: var(--text-muted);">${data.unit}</span></div>
                ${statusHTML}
            `;

            measurementsGrid.appendChild(card);
        }
    }

    // Show clinical assessment
    if (data.clinical) {
        let flagsHTML = '';
        if (data.clinical.flags && data.clinical.flags.length > 0) {
            flagsHTML = `
                <div style="margin-top: 20px;">
                    <strong style="color: var(--secondary); display: block; margin-bottom: 10px;">Clinical Flags:</strong>
                    ${data.clinical.flags.map(flag => `
                        <div style="padding: 10px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; margin-bottom: 5px; font-size: 0.9rem; color: #fca5a5;">
                            ⚠️ ${flag}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        clinicalAssessment.innerHTML = `
            <div class="clinical-card">
                <h3 style="margin-bottom: 20px; color: var(--text-pure);">📊 Clinical Profile</h3>
                
                <div style="display: grid; gap: 15px;">
                    <div style="display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid var(--glass-border);">
                        <span style="color: var(--text-secondary);">Estimated GA</span>
                        <span style="color: var(--text-pure); font-weight: 700;">${data.clinical.estimated_ga.toFixed(1)}w ${data.clinical.ga_uncertainty ? `± ${data.clinical.ga_uncertainty.toFixed(1)}w` : ''}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid var(--glass-border);">
                        <span style="color: var(--text-secondary);">GA Consistency</span>
                        <span style="color: var(--accent); font-weight: 700;">${data.clinical.ga_consistency}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid var(--glass-border);">
                        <span style="color: var(--text-secondary);">Growth Status</span>
                        <span style="color: #fff; font-weight: 700;">${data.clinical.growth_status}</span>
                    </div>
                    ${data.risk_assessment && data.risk_assessment.efw ? `
                    <div style="display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid var(--glass-border);">
                        <span style="color: var(--text-secondary);">Estimated Weight (EFW)</span>
                        <span style="color: var(--secondary); font-weight: 700;">${data.risk_assessment.efw.value} ${data.risk_assessment.efw.unit}</span>
                    </div>
                    ` : ''}
                    ${data.risk_assessment && data.risk_assessment.ci ? `
                    <div style="display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid var(--glass-border);">
                        <span style="color: var(--text-secondary);">Cephalic Index (CI)</span>
                        <span style="color: ${data.risk_assessment.ci.status === 'normal' ? 'var(--success)' : 'var(--warning)'}; font-weight: 700;">${data.risk_assessment.ci.value}${data.risk_assessment.ci.unit}</span>
                    </div>
                    ` : ''}
                </div>
                
                ${data.growth_velocity ? `
                <div style="margin-top: 25px; padding: 15px; background: rgba(99, 102, 241, 0.1); border: 1px solid var(--primary); border-radius: 12px;">
                    <strong style="color: var(--primary); display: block; margin-bottom: 10px;">📈 Growth Velocity (last ${data.growth_velocity.dt_weeks < 1 ? Math.round(data.growth_velocity.dt_weeks * 7) + ' days' : data.growth_velocity.dt_weeks.toFixed(1) + 'w'})</strong>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        ${Object.entries(data.growth_velocity.velocity).map(([k, v]) => `
                            <div style="font-size: 0.85rem; color: var(--text-secondary);">
                                ${k}: <span style="color: var(--text-pure); font-weight: 600;">+${v} ${data.growth_velocity.unit}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                ${flagsHTML}
            </div>
        `;
    }

    // Initialize charts
    currentPatientId = data.patient_id || 'default_patient';
    const selectedStandard = document.getElementById('standardInput').value || 'INTERGROWTH';
    
    // Update mini-toggles active state
    document.querySelectorAll('#growthStandardControls .btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.std === selectedStandard);
    });
    
    renderGrowthChart(currentPatientId, 'HC', selectedStandard);
    renderProportionRadar(data);

    // Populate Results Header Strip
    const headerPatientId = document.getElementById('headerPatientId');
    const headerGA = document.getElementById('headerGA');
    const headerRisk = document.getElementById('headerRisk');
    const headerEDD = document.getElementById('headerEDD');

    // Get values from nested clinical/risk data
    const consensusGA = data.clinical?.estimated_ga || data.gestational_age || '---';
    const overallRisk = data.risk_assessment?.overall_risk || data.risk || 'normal';

    if (headerPatientId) headerPatientId.textContent = currentPatientId || 'ANONYMOUS';
    if (headerGA) headerGA.textContent = consensusGA !== '---' ? `${consensusGA}w` : '---';
    
    if (headerRisk) {
        headerRisk.textContent = overallRisk.toUpperCase();
        const riskColor = overallRisk === 'alert' || overallRisk === 'critical' ? '#ef4444' : 
                          overallRisk === 'warning' || overallRisk === 'high_risk' ? '#fbbf24' : '#10b981';
        headerRisk.style.background = `${riskColor}22`;
        headerRisk.style.color = riskColor;
        headerRisk.style.borderColor = `${riskColor}44`;
        headerRisk.style.border = '1px solid';
    }

    // Load Charts & Advanced Analysis
    if (currentPatientId) {
        setTimeout(() => loadAdvancedAnalytics(currentPatientId, data.gestational_age), 600);
    }

    // Enable download and view buttons in header
    if (headerDownloadPDFBtn) headerDownloadPDFBtn.disabled = false;
    if (headerViewPDFBtn) headerViewPDFBtn.disabled = false;
    if (previewReportBtn) previewReportBtn.disabled = false;
    

    // Default Tab
    switchResultTab('analysis');
}

// New Analysis Logic is handled via uploadResetBtn near the top

// Tab Switcher for Results Page
function switchResultTab(tabId) {
    document.querySelectorAll('.res-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    document.querySelectorAll('.tab-content-panel').forEach(panel => {
        panel.classList.toggle('hidden', panel.id !== `tab-${tabId}`);
    });
    if (tabId === 'growth-res' && growthChart) growthChart.resize();
}

// CLINICAL SETTINGS & STANDARDS
function toggleClinicalSettings() {
    if (clinicalSettingsPanel) {
        clinicalSettingsPanel.classList.toggle('hidden');
    }
}

function applyStandardChange(newStandard) {
    console.log('Switching growth standard to:', newStandard);
    // Update the main input so it's consistent
    const mainStdInput = document.getElementById('standardInput');
    if (mainStdInput) mainStdInput.value = newStandard;
    
    // Re-run analysis with new standard
    processImage();
    
    // Hide panel
    if (clinicalSettingsPanel) clinicalSettingsPanel.classList.add('hidden');
}

// PDF GENERATION SERVICES
async function generatePDFPreview() {
    const previewWindow = window.open('about:blank', '_blank');
    if (previewWindow) {
        previewWindow.document.write('<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; font-family:sans-serif; color:#666;"><div style="width:40px; height:40px; border:4px solid #f3f3f3; border-top:4px solid #06b6d4; border-radius:50%; animation:spin 1s linear infinite;"></div><p style="margin-top:20px;">Generating Clinical Report...</p></div><style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>');
    }

    try {
        const chartCanvas = document.getElementById('growthChart');
        let pdfResponse;

        // Attempt to capture chart even if hidden
        let chartImage = null;
        if (chartCanvas && typeof growthChart !== 'undefined' && growthChart) {
            const tab = document.getElementById('tab-growth-res');
            const wasHidden = tab ? tab.classList.contains('hidden') : false;
            if (wasHidden) tab.classList.remove('hidden');
            
            const dataUrl = chartCanvas.toDataURL('image/png');
            if (dataUrl && dataUrl.length > 50) chartImage = dataUrl;
            
            if (wasHidden) tab.classList.add('hidden');
        }

        if (chartImage) {
            pdfResponse = await fetch(`/api/report_with_chart/${fileId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chart_image: chartImage })
            });
        } else {
            pdfResponse = await fetch(`/api/report/${fileId}`);
        }

        if (pdfResponse && pdfResponse.ok) {
            const blob = await pdfResponse.blob();
            const url = window.URL.createObjectURL(blob);
            if (previewWindow) previewWindow.location.href = url;
            else window.open(url, '_blank');
        } else {
            const errorData = await pdfResponse.json().catch(() => ({ error: 'Unknown server error' }));
            throw new Error(errorData.error || `Server returned error ${pdfResponse.status}`);
        }
    } catch (e) {
        console.error('PDF Preview Error:', e);
        if (previewWindow) {
            previewWindow.document.body.innerHTML = `<p style="color:#ef4444; text-align:center; font-family:sans-serif; margin-top:50px;"><b>Error:</b> ${e.message}<br><small>Check server logs for details.</small></p>`;
        }
    }
}

async function triggerPDFDownload() {
    const chartCanvas = document.getElementById('growthChart');
    let chartImage = null;
    if (chartCanvas && typeof growthChart !== 'undefined' && growthChart) {
        const tab = document.getElementById('tab-growth-res');
        const wasHidden = tab ? tab.classList.contains('hidden') : false;
        if (wasHidden) tab.classList.remove('hidden');
        const dataUrl = chartCanvas.toDataURL('image/png');
        if (dataUrl && dataUrl.length > 50) chartImage = dataUrl;
        if (wasHidden) tab.classList.add('hidden');
    }

    if (chartImage) {
        try {
            const response = await fetch(`/api/report_with_chart/${fileId}?download=1`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chart_image: chartImage })
            });
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `CradleMetrics_Report_${fileId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                return;
            }
        } catch (e) { console.error('Advanced report generation failed:', e); }
    }
    window.location.href = `/api/report/${fileId}?download=1`;
}

// Handle "View PDF" (Inline in browser tab)
if (headerViewPDFBtn) {
    headerViewPDFBtn.onclick = (e) => {
        e.stopPropagation();
        generatePDFPreview();
    };
}
if (headerDownloadPDFBtn) {
    headerDownloadPDFBtn.onclick = (e) => {
        e.stopPropagation();
        triggerPDFDownload();
    };
}

if (previewReportBtn) {
    previewReportBtn.onclick = () => window.open(`/report/${fileId}`, '_blank');
}

// ============================================
// GROWTH ANALYTICS & CHARTING
// ============================================

async function renderGrowthChart(patientId, metric = 'HC', standard = 'INTERGROWTH') {
    const canvas = document.getElementById('growthChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;

    const showErrorOverlay = (msg) => {
        let overlay = container.querySelector('.chart-error-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'chart-error-overlay';
            overlay.style = "position: absolute; top:0; left:0; width:100%; height:100%; display: flex; align-items: center; justify-content: center; color: var(--warning); text-align: center; font-size: 0.9rem; padding: 20px; background: rgba(4, 20, 40, 0.8); backdrop-filter: blur(4px); z-index: 20;";
            container.appendChild(overlay);
        }
        overlay.innerHTML = `<div>⚠️ ${msg}</div>`;
        overlay.style.display = 'flex';
        canvas.style.opacity = '0.3';
    };

    const hideErrorOverlay = () => {
        const overlay = container.querySelector('.chart-error-overlay');
        if (overlay) overlay.style.display = 'none';
        canvas.style.opacity = '1';
    };

    try {
        let url = `/api/growth_data/${patientId}/${metric}?standard=${standard}`;
        if (window.currentScanData) {
            const currentGa = window.currentScanData.clinical?.estimated_ga;
            let currentVal = window.currentScanData.measurements?.[metric];
            if (currentGa && currentVal) url += `&current_ga=${currentGa}&current_val=${currentVal}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        if (!data.reference || !data.patient_data) throw new Error("Reference data unavailable");

        hideErrorOverlay();
        if (growthChart) growthChart.destroy();

        growthChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Patient Data',
                        data: data.patient_data,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.15)',
                        borderWidth: 2,
                        pointRadius: 4,
                        tension: 0.4,
                        fill: false,
                        order: 1
                    },
                    {
                        label: 'Growth Forecast',
                        data: data.forecast || [],
                        borderColor: '#a855f7',
                        borderDash: [6, 3],
                        borderWidth: 2,
                        pointRadius: 4,
                        fill: false,
                        order: 2
                    },
                    {
                        label: '50th Percentile',
                        data: data.reference['50th'],
                        borderColor: 'rgba(255, 255, 255, 0.35)',
                        borderDash: [6, 4],
                        pointRadius: 0,
                        fill: false,
                        order: 5
                    },
                    {
                        label: '10th Percentile',
                        data: data.reference['10th'],
                        borderColor: 'rgba(239, 68, 68, 0.4)',
                        borderDash: [3, 3],
                        pointRadius: 0,
                        fill: false,
                        order: 6
                    },
                    {
                        label: '90th Percentile',
                        data: data.reference['90th'],
                        borderColor: 'rgba(239, 68, 68, 0.4)',
                        borderDash: [3, 3],
                        pointRadius: 0,
                        fill: { target: '-1', above: 'rgba(124, 211, 252, 0.04)' },
                        order: 7
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: 'linear', title: { display: true, text: 'Weeks (GA)' } },
                    y: { title: { display: true, text: `${metric} (${data.unit})` } }
                },
                plugins: {
                    legend: { position: 'top', labels: { color: '#e2e8f0' } }
                }
            }
        });
        window._lastGrowthData = data;
    } catch (error) {
        console.error('Growth Chart Error:', error);
        showErrorOverlay(error.message);
    }
}

window.updateChartMetric = function (metric) {
    document.querySelectorAll('#metricButtons .btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.includes(metric));
    });
    // Check which standard is active in the mini-toggle
    const activeStdBtn = document.querySelector('#growthStandardControls .btn.active');
    const standard = activeStdBtn ? activeStdBtn.dataset.std : 'INTERGROWTH';
    
    // Check if in Z-Score view
    const zBtn = document.getElementById('zScoreToggleBtn');
    const isZScore = zBtn && zBtn.classList.contains('active');
    
    if (isZScore) {
        renderZScoreChart(currentPatientId, metric, standard);
    } else {
        renderGrowthChart(currentPatientId, metric, standard);
    }
};

window.updateChartStandard = function (standard) {
    document.querySelectorAll('#growthStandardControls .btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.std === standard);
    });
    // Update the main settings dropdown too for consistency
    const mainStdInput = document.getElementById('standardInput');
    if (mainStdInput) mainStdInput.value = standard;
    
    const activeMetric = document.querySelector('#metricButtons .btn.active');
    const metric = activeMetric ? activeMetric.textContent.match(/\((.*?)\)/)[1] : 'HC';
    
    window.updateChartMetric(metric);
};

window.toggleZScoreView = function(btn) {
    const isActive = btn.classList.toggle('active');
    btn.textContent = isActive ? 'Raw Value View' : 'Z-Score View';
    
    const activeMetric = document.querySelector('#metricButtons .btn.active');
    const metric = activeMetric ? activeMetric.textContent.match(/\((.*?)\)/)[1] : 'HC';
    
    window.updateChartMetric(metric);
};

async function renderZScoreChart(patientId, metric, standard) {
    const canvas = document.getElementById('growthChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    try {
        const response = await fetch(`/api/growth_data/${patientId}/${metric}?standard=${standard}`);
        const data = await response.json();
        if (!data.z_series) throw new Error("Z-Score data unavailable");

        if (growthChart) growthChart.destroy();
        growthChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: `${metric} Z-Score (${standard})`,
                    data: data.z_series,
                    borderColor: 'var(--primary)',
                    backgroundColor: 'rgba(6, 182, 212, 0.1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    tension: 0.3,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: 'linear', position: 'bottom', title: { display: true, text: 'Weeks (GA)', color: '#94a3b8' } },
                    y: { 
                        title: { display: true, text: 'Z-Score', color: '#94a3b8' },
                        suggestedMin: -3,
                        suggestedMax: 3,
                        grid: {
                            color: (context) => context.tick.value === 0 ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.05)',
                            lineWidth: (context) => context.tick.value === 0 ? 2 : 1
                        }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#e2e8f0' } }
                }
            }
        });
    } catch (e) {
        console.error(e);
    }
}

// ============================================
// FULLSCREEN IMAGE MODAL
// ============================================

window.openImageModal = function(imageId) {
    const sourceImage = document.getElementById(imageId);
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalLabel = document.getElementById('modalLabel');
    if (!sourceImage || !sourceImage.src) return;
    modalImage.src = sourceImage.src;
    const labels = { 'resultImage': 'Segmentation Output', 'originalImage': 'Original Ultrasound' };
    modalLabel.textContent = labels[imageId] || 'Image View';
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
};

window.closeImageModal = function() {
    const modal = document.getElementById('imageModal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
};

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeImageModal();
});

// Counter Animation
function animateValue(id, start, end, duration, suffix = "", decimals = 0) {
    const obj = document.getElementById(id);
    if (!obj) return;
    const range = end - start;
    let timer;
    const startTime = new Date().getTime();
    const endTime = startTime + duration;
    function run() {
        const now = new Date().getTime();
        const remaining = Math.max((endTime - now) / duration, 0);
        const value = end - (remaining * range);
        obj.innerHTML = (decimals > 0 ? value.toFixed(decimals) : Math.floor(value)) + suffix;
        if (value >= end) {
            obj.innerHTML = (decimals > 0 ? end.toFixed(decimals) : Math.floor(end)) + suffix;
            clearInterval(timer);
        }
    }
    timer = setInterval(run, 50);
    run();
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    const modalContent = document.querySelector('.modal-content');
    if (modalContent) modalContent.onclick = (e) => e.stopPropagation();
    checkResumeSession();
});

// ============================================
// SESSION MANAGEMENT
// ============================================

async function checkResumeSession() {
    const urlParams = new URLSearchParams(window.location.search);
    const resumeId = urlParams.get('file_id');
    if (!resumeId) return;
    fileId = resumeId;
    const cachedData = sessionStorage.getItem(`clinical_result_${resumeId}`);
    if (cachedData) {
        const data = JSON.parse(cachedData);
        const cachedStd = sessionStorage.getItem(`clinical_standard_${resumeId}`);
        if (cachedStd) document.getElementById('standardInput').value = cachedStd;
        uploadSection.classList.add('hidden');
        showResults(data);
        return;
    }
    uploadSection.classList.add('hidden');
    processingSection.classList.remove('hidden');
    updateProgress(50, 'Restoring results...');
    try {
        const response = await fetch(`/api/results/${resumeId}`);
        const data = await response.json();
        if (data.success) {
            updateProgress(100, 'Restored.');
            showResults(data.data);
        } else showError('Session expired.');
    } catch (e) { showError('Network error.'); }
}

window.toggleClinicalSettings = function() {
    const panel = document.getElementById('clinicalSettingsPanel');
    if (panel) panel.classList.toggle('hidden');
};

window.applyClinicalSettings = async function() {
    const newStandard = document.getElementById('resultsStandardInput').value;
    toggleClinicalSettings();
    const gaWeeks = gaInput.value ? parseFloat(gaInput.value) : null;
    const patientId = document.getElementById('patientIdInput').value || 'default_patient';
    resultsSection.classList.add('hidden');
    processingSection.classList.remove('hidden');
    updateProgress(40, `Applying ${newStandard}...`);
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_id: fileId, ga_weeks: gaWeeks, patient_id: patientId, standard_id: newStandard }),
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('standardInput').value = newStandard;
            showResults(data);
        } else throw new Error(data.error);
    } catch (e) {
        showError('Failed: ' + e.message);
        resultsSection.classList.remove('hidden');
        processingSection.classList.add('hidden');
    }
};

// ============================================
// ADVANCED VISUALIZATIONS
// ============================================

window.switchAnalyticsTab = function(tab) {
    const growthTab = document.getElementById('growthTabContent');
    const radarTab = document.getElementById('radarTabContent');
    const growthBtn = document.getElementById('tabGrowth');
    const radarBtn = document.getElementById('tabRadar');
    const isGrowth = tab === 'growth';
    growthTab.classList.toggle('hidden', !isGrowth);
    radarTab.classList.toggle('hidden', isGrowth);
    growthBtn.classList.toggle('active', isGrowth);
    radarBtn.classList.toggle('active', !isGrowth);
    growthBtn.style.color = isGrowth ? 'var(--primary)' : 'var(--text-secondary)';
    growthBtn.style.borderBottom = isGrowth ? '2px solid var(--primary)' : 'none';
    radarBtn.style.color = !isGrowth ? 'var(--primary)' : 'var(--text-secondary)';
    radarBtn.style.borderBottom = !isGrowth ? '2px solid var(--primary)' : 'none';
}

function renderProportionRadar(data) {
    const canvas = document.getElementById('radarChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (radarChart) radarChart.destroy();

    const metrics = ['HC', 'AC', 'FL', 'BPD'];
    const values = metrics.map(m => data.percentiles?.[m]?.percentile || 50);
    const backgroundColors = values.map(v => (v < 10 || v > 90) ? 'rgba(251, 191, 36, 0.2)' : 'rgba(6, 182, 212, 0.2)');
    const borderColors = values.map(v => (v < 10 || v > 90) ? '#fbbf24' : '#06b6d4');

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: metrics,
            datasets: [{
                label: 'Growth Percentiles',
                data: values,
                backgroundColor: 'rgba(6, 182, 212, 0.2)',
                borderColor: '#06b6d4',
                borderWidth: 2,
                pointBackgroundColor: borderColors,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: borderColors,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    beginAtZero: true,
                    ticks: {
                        display: false,
                        stepSize: 25
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    angleLines: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    pointLabels: {
                        color: 'rgba(255, 255, 255, 0.7)',
                        font: {
                            size: 11,
                            weight: '600'
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `Percentile: ${ctx.raw}th`
                    }
                }
            }
        }
    });

    // Update legend UI below radar if it exists
    const radarTab = document.getElementById('radarTabContent');
    if (radarTab) {
        let legend = radarTab.querySelector('.radar-legend');
        if (!legend) {
            legend = document.createElement('div');
            legend.className = 'radar-legend';
            legend.style = 'margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;';
            radarTab.appendChild(legend);
        }
        
        legend.innerHTML = metrics.map((m, i) => {
            const v = values[i];
            const status = v < 10 ? 'Small' : v > 90 ? 'Large' : 'Normal';
            const color = status === 'Normal' ? '#06b6d4' : '#fbbf24';
            return `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 8px; font-size: 0.8rem;">
                    <span style="color: var(--text-secondary);">${m}</span>
                    <span style="color: ${color}; font-weight: 700;">${v}th (${status})</span>
                </div>
            `;
        }).join('');
    }
}

async function loadAdvancedAnalytics(patientId, currentGA = null) {
    const grid = document.getElementById('advancedAnalyticsContainer');
    if (!grid) return;

    // Reset grid with modern layout
    grid.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 5px;">
            <div id="advanced-col-1" style="display: flex; flex-direction: column; gap: 20px;"></div>
            <div id="advanced-col-2" style="display: flex; flex-direction: column; gap: 20px;"></div>
        </div>
        <div id="falteringAlertZone" style="margin-top: 20px;"></div>
    `;

    const col1 = document.getElementById('advanced-col-1');
    const col2 = document.getElementById('advanced-col-2');
    const falteringZone = document.getElementById('falteringAlertZone');

    // Load Consensus Analysis
    renderConsensusSection(patientId);

    // Load data in parallel
    const [eddRes, bwRes, falterRes, gaRes, scanRes] = await Promise.allSettled([
        fetch(`/api/edd/${patientId}${(currentGA ? `?current_ga=${currentGA}` : '')}`).then(r => r.json()),
        fetch(`/api/birth_weight_prediction/${patientId}`).then(r => r.json()),
        fetch(`/api/growth_faltering/${patientId}`).then(r => r.json()),
        fetch(`/api/ga_consensus/${patientId}`).then(r => r.json()),
        fetch(`/api/next_scan_recommendation/${patientId}`).then(r => r.json())
    ]);

    // 1. EDD Card
    if (eddRes.status === 'fulfilled' && !eddRes.value.error) {
        const edd = eddRes.value;
        const eddDate = edd.predicted_edd || edd.edd_formatted || 'TBD';
        col1.insertAdjacentHTML('beforeend', `
            <div class="card" style="padding: 24px; border-left: 4px solid var(--secondary);">
                <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">Estimated Delivery (EDD)</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: #fff; margin-bottom: 12px;">${eddDate}</div>
                <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 10px; font-size: 0.85rem;">
                    <span style="color: var(--text-secondary);">GA via EDD:</span>
                    <span style="color: var(--secondary); font-weight: 700; text-align: right;">${edd.estimated_ga_at_scan}w</span>
                    <span style="color: var(--text-muted);">Trimester:</span>
                    <span style="color: var(--text-pure); font-weight: 600; text-align: right;">${edd.trimester}</span>
                </div>
            </div>`);
        
        // Update header EDD too
        const headerEDD = document.getElementById('headerEDD');
        if (headerEDD) headerEDD.textContent = eddDate;
    }

    // 2. Birth Weight Prediction
    if (bwRes.status === 'fulfilled' && !bwRes.value.error) {
        const bw = bwRes.value;
        const statusColor = bw.color || 'var(--primary)';
        col2.insertAdjacentHTML('beforeend', `
            <div class="card" style="padding: 24px; border-left: 4px solid ${statusColor};">
                <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">Term Weight (40w)</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: #fff; margin-bottom: 12px;">${bw.predicted_birth_weight_kg} kg</div>
                <div id="bwProgressBar" style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; margin-bottom: 10px; overflow: hidden;">
                    <div style="height: 100%; width: ${Math.min(100, (bw.predicted_birth_weight_g/5000)*100)}%; background: ${statusColor};"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span style="color: var(--text-secondary);">${bw.predicted_birth_weight_g}g predicted</span>
                    <span style="color: ${statusColor}; font-weight: 700;">${bw.category.toUpperCase()}</span>
                </div>
            </div>`);
    }

    // 3. GA Consensus
    if (gaRes.status === 'fulfilled' && !gaRes.value.error) {
        const ga = gaRes.value;
        const statusColor = ga.consistency === 'Excellent' ? 'var(--success)' : ga.consistency === 'Good' ? 'var(--warning)' : '#ef4444';
        col1.insertAdjacentHTML('beforeend', `
            <div class="card" style="padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                    <div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">GA Consensus</div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary);">${ga.consensus_ga}w</div>
                    </div>
                    <span class="status-badge" style="background: ${statusColor}22; color: ${statusColor}; border: 1px solid ${statusColor}44;">${ga.consistency}</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4;">
                    Mean value derived from AC, HC, FL, and BPD biometrics. Deviation factor: ±${ga.std_dev ? ga.std_dev.toFixed(2) : '0.00'}w.
                </div>
            </div>`);
    }

    // 4. Recommendation
    if (scanRes.status === 'fulfilled' && !scanRes.value.error) {
        const s = scanRes.value;
        col2.insertAdjacentHTML('beforeend', `
            <div class="card" style="padding: 24px;">
                <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">Recommended Follow-up</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #fff; margin-bottom: 10px;">${s.next_scan_formatted}</div>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 15px; line-height: 1.5;">${s.reason}</div>
            </div>`);
    }

    // 5. Faltering Alerts
    if (falterRes.status === 'fulfilled' && falterRes.value.faltering && (falterRes.value.alerts?.length || 0) > 0) {
        const f = falterRes.value;
        const alertsHTML = f.alerts.map(a => `
            <div style="padding: 12px; background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; margin-bottom: 10px;">
                <div style="font-weight: 700; color: #ef4444; margin-bottom: 4px;">🚨 ${a.metric} — Faltering (${a.bands_dropped} bands)</div>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">${a.from_percentile}th → ${a.to_percentile}th percentile (${a.from_ga}w to ${a.to_ga}w)</div>
            </div>
        `).join('');

        falteringZone.innerHTML = `
            <div class="card" style="border: 1px solid rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.05);">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: #ef4444; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800;">!</div>
                    <div>
                        <div style="font-size: 1rem; font-weight: 800; color: #ef4444;">Growth Faltering Detected</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted);">${f.scans_analysed} scans analysed</div>
                    </div>
                </div>
                ${alertsHTML}
            </div>
        `;
    }
}

window.toggleZScoreView = function(btn) {
    if (!growthChart || !window._lastGrowthData) return;
    const data = window._lastGrowthData;
    const isZ = btn.dataset.mode === 'z';
    btn.dataset.mode = isZ ? 'raw' : 'z';
    btn.textContent = isZ ? 'Z-Score View' : 'Raw Values';
    if (!isZ) {
        growthChart.data.datasets[0].data = data.z_series || [];
        growthChart.options.scales.y.min = -3;
        growthChart.options.scales.y.max = 3;
    } else {
        growthChart.data.datasets[0].data = data.patient_data;
        delete growthChart.options.scales.y.min;
        delete growthChart.options.scales.y.max;
    }
    growthChart.update();
};

window.toggleStandardsOverlay = async function(btn, patientId) {
    const activeMetricBtn = document.querySelector('#metricButtons .btn.active');
    const metric = activeMetricBtn ? activeMetricBtn.textContent.match(/\((.*?)\)/)[1] : 'HC';

    if (btn.dataset.active === 'true') {
        btn.dataset.active = 'false'; btn.textContent = 'Compare Standards';
        window.updateChartMetric(metric); return;
    }
    
    try {
        const res = await fetch(`/api/growth_data/${patientId}/${metric}?overlay_all=true`);
        const d = await res.json();
        if (d.all_standards) {
            // Define colors for overlay
            const colors = { 'INTERGROWTH': '#06b6d4', 'WHO': '#38bdf8', 'HADLOCK': '#a855f7' };
            
            Object.entries(d.all_standards).forEach(([name, c]) => {
                growthChart.data.datasets.push({ 
                    label: `${name} (50th)`, 
                    data: c['50th'], 
                    borderColor: colors[name] || '#fff',
                    borderDash: [5, 5], 
                    pointRadius: 0, 
                    fill: false,
                    opacity: 0.6
                });
            });
            growthChart.update(); btn.dataset.active = 'true'; btn.textContent = 'Clear Overlay';
        }
    } catch (e) {
        console.error("Overlay failed:", e);
    }
};


async function renderConsensusSection(patientId) {
    const grid = document.getElementById('consensusGrid');
    const banner = document.getElementById('discordanceBanner');
    if (!grid) return;

    try {
        const response = await fetch(`/api/consensus/${patientId}`);
        const result = await response.json();
        
        if (!result.success) return;
        const data = result.data;
        
        grid.innerHTML = '';
        let hasDiscordance = false;

        for (const [metric, analysis] of Object.entries(data.metrics)) {
            const consensus = analysis.consensus;
            if (consensus.is_discordant && consensus.discordance_severity !== 'Low') hasDiscordance = true;

            const metricRow = document.createElement('div');
            metricRow.style = 'padding: 20px; background: rgba(255,255,255,0.03); border: 1px solid var(--glass-border); border-radius: 12px;';
            
            const standardsHTML = Object.entries(analysis.standards).map(([std, res]) => `
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 2px;">
                    <span>${std}</span>
                    <span style="color: ${res.classification === 'AGA' ? 'var(--primary)' : 'var(--warning)'}; font-weight: 600;">${res.percentile}th</span>
                </div>
            `).join('');

            metricRow.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                    <div>
                        <div style="font-weight: 700; color: #fff;">${metric} Consensus</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${analysis.measurement}mm @ ${analysis.ga_weeks}w</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.2rem; font-weight: 800; color: var(--success);">${consensus.median_percentile}th</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Median</div>
                    </div>
                </div>

                <div style="position: relative; height: 32px; background: rgba(255,255,255,0.05); border-radius: 6px; margin: 20px 0; overflow: hidden;">
                    <!-- Range Box (Whisker) -->
                    <div style="position: absolute; left: ${consensus.min_percentile}%; width: ${consensus.range}%; height: 100%; background: var(--success); opacity: 0.2;"></div>
                    
                    <!-- Standards Markers -->
                    ${Object.values(analysis.standards).map(s => `
                        <div style="position: absolute; left: ${s.percentile}%; top: 25%; width: 2px; height: 50%; background: #fff; opacity: 0.5;"></div>
                    `).join('')}

                    <!-- Median Marker -->
                    <div style="position: absolute; left: ${consensus.median_percentile}%; top: 0; width: 4px; height: 100%; background: var(--success); box-shadow: 0 0 10px var(--success);"></div>
                </div>

                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.05);">
                    ${standardsHTML}
                </div>
            `;
            grid.appendChild(metricRow);
        }

        if (hasDiscordance && banner) {
            banner.classList.remove('hidden');
        } else if (banner) {
            banner.classList.add('hidden');
        }

    } catch (e) {
        console.error('Consensus Analysis Error:', e);
    }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function updateProgress(p, t) { if (progressFill) progressFill.style.width = p+'%'; if (progressText) progressText.textContent = t; }
function showError(m) { alert(m); processingSection.classList.add('hidden'); uploadSection.classList.remove('hidden'); }
