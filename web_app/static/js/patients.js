// Patient Directory JavaScript

let allPatients = [];
let modalChart = null;
let currentPatientId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadPatients();

    const searchInput = document.getElementById('patientSearch');
    searchInput.addEventListener('input', (e) => {
        filterPatients(e.target.value);
    });
});

async function loadPatients() {
    try {
        const response = await fetch('/api/patients');
        const data = await response.json();

        allPatients = data.patients || [];
        renderPatientList(allPatients);
        calcComparativeStats(allPatients);

        document.getElementById('patientCount').textContent = allPatients.length;

        if (allPatients.length === 0) {
            document.getElementById('patientTableContainer').classList.add('hidden');
            document.getElementById('noPatients').classList.remove('hidden');
            document.getElementById('comparativeStats').classList.add('hidden');
        } else {
            document.getElementById('patientTableContainer').classList.remove('hidden');
            document.getElementById('noPatients').classList.add('hidden');
            document.getElementById('comparativeStats').classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error loading patients:', error);
    }
}

function calcComparativeStats(patients) {
    if (!patients.length) return;

    const total = patients.length;
    let highRiskCount = 0;
    let totalGA = 0;
    let countedGA = 0;
    const distribution = { normal: 0, warning: 0, alert: 0 };

    patients.forEach(p => {
        const risk = p.latest_risk || 'normal';
        distribution[risk] = (distribution[risk] || 0) + 1;
        if (risk === 'alert' || risk === 'high_risk') highRiskCount++;

        if (p.latest_ga) {
            totalGA += p.latest_ga;
            countedGA++;
        }
    });

    document.getElementById('statTotal').textContent = total;
    document.getElementById('statRisk').textContent = Math.round((highRiskCount / total) * 100) + '%';
    document.getElementById('statGA').textContent = countedGA > 0 ? (totalGA / countedGA).toFixed(1) + 'w' : '---';

    // Render Mini Distribution Chart
    const ctx = document.getElementById('riskDistributionChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Normal', 'Warning', 'Alert'],
            datasets: [{
                data: [distribution.normal, distribution.warning, distribution.alert || distribution.high_risk || 0],
                backgroundColor: ['#10b981', '#fbbf24', '#ef4444'],
                borderRadius: 4,
                barThickness: 20
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false, grid: { display: false } },
                y: { ticks: { color: 'rgba(255,255,255,0.7)', font: { size: 10 } }, grid: { display: false } }
            }
        }
    });
}

function renderPatientList(patients) {
    const list = document.getElementById('patientList');
    list.innerHTML = '';

    patients.forEach(p => {
        const tr = document.createElement('tr');
        tr.onclick = () => showPatientHistory(p.patient_id);

        const risk = p.latest_risk || 'normal';
        const riskClass = `status-${risk}`;

        tr.innerHTML = `
            <td style="font-weight: 600;">${p.patient_id}</td>
            <td>${p.last_scan}</td>
            <td>${p.latest_ga ? p.latest_ga.toFixed(1) + 'w' : 'N/A'}</td>
            <td><span class="status-pill ${riskClass}">${risk}</span></td>
            <td><button class="btn btn-sm" style="background: rgba(255,255,255,0.05); color: #fff;">View Full History</button></td>
        `;
        list.appendChild(tr);
    });
}

function filterPatients(query) {
    const filtered = allPatients.filter(p =>
        p.patient_id.toLowerCase().includes(query.toLowerCase())
    );
    renderPatientList(filtered);
}

async function showPatientHistory(patientId) {
    currentPatientId = patientId;
    document.getElementById('modalPatientId').textContent = `Patient: ${patientId}`;
    document.getElementById('historyModal').classList.remove('hidden');

    const response = await fetch(`/api/history/${patientId}`);
    const data = await response.json();

    // Render timeline (limit to latest 50 for performance, reverse for newest first)
    const timeline = document.getElementById('scanTimeline');
    timeline.innerHTML = '';

    const displayHistory = [...data.history].reverse().slice(0, 50);

    displayHistory.forEach(scan => {
        const div = document.createElement('div');
        div.style.padding = '12px';
        div.style.background = 'rgba(255,255,255,0.03)';
        div.style.borderRadius = '10px';
        div.style.cursor = 'pointer';
        div.style.border = '1px solid rgba(255,255,255,0.05)';

        const ga = scan.data?.clinical?.estimated_ga;
        const risk = scan.data?.risk_assessment?.growth || 'Complete';
        const dateStr = new Date(scan.timestamp).toLocaleDateString() + ' ' + new Date(scan.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        div.onclick = (e) => {
            e.stopPropagation();
            window.location.href = `/analyze?file_id=${scan.record_id}`;
        };

        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                <span style="color: #fff; font-weight: 500;">${dateStr}</span>
                <span style="color: var(--text-muted);">${ga ? ga.toFixed(1) + 'w' : 'N/A'}</span>
            </div>
            <div style="margin-top: 5px; font-size: 0.75rem; color: var(--text-secondary);">
                ${risk}
            </div>
        `;
        timeline.appendChild(div);
    });

    // Initialize chart
    updateModalChart('HC');
}

async function updateModalChart(metric) {
    // Update button states
    const buttons = document.querySelectorAll('#metricSwitches .btn');
    buttons.forEach(btn => {
        if (btn.textContent === metric) btn.classList.add('active');
        else btn.classList.remove('active');
    });

    if (modalChart) modalChart.destroy();

    const response = await fetch(`/api/growth_data/${currentPatientId}/${metric}`);
    const data = await response.json();

    const ctx = document.getElementById('modalGrowthChart').getContext('2d');
    modalChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Patient Data',
                    data: data.patient_data,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    pointRadius: 2,
                    pointHoverRadius: 5,
                    fill: false,
                    zIndex: 10,
                    tension: 0.3
                },
                {
                    label: 'Reference (50th)',
                    data: data.reference['50th'],
                    borderColor: 'rgba(255, 255, 255, 0.4)',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                    borderWidth: 1
                },
                {
                    label: 'Normal Range (10th-90th)',
                    data: data.reference['90th'],
                    borderColor: 'rgba(16, 185, 129, 0.1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    fill: 2, // Fill to the next dataset (10th)
                    pointRadius: 0,
                    borderWidth: 1
                },
                {
                    label: '10th %ile',
                    data: data.reference['10th'],
                    borderColor: 'rgba(16, 185, 129, 0.1)',
                    pointRadius: 0,
                    fill: false,
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            scales: {
                x: {
                    type: 'linear',
                    min: 14,
                    max: 42,
                    title: { display: true, text: 'Gestational Age (Weeks)', color: 'rgba(255,255,255,0.5)' },
                    ticks: { color: 'rgba(255,255,255,0.5)', stepSize: 2 },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    title: { display: true, text: `${metric} (${data.unit})`, color: 'rgba(255,255,255,0.5)' },
                    ticks: { color: 'rgba(255,255,255,0.5)' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    labels: { color: 'rgba(255,255,255,0.7)', boxWidth: 12, usePointStyle: true }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(1) + ' ' + data.unit;
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

window.closeModal = function () {
    document.getElementById('historyModal').classList.add('hidden');
}
