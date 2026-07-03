/* Shared report-rendering helpers, used by app.js (post-upload card) and
   report_detail.js (standalone report page). Must be loaded before both. */

const METRIC_ORDER = ['pigmentation', 'acne', 'redness', 'wrinkles', 'pores'];

function formatDate(iso) {
    return new Date(iso).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
}

function severityForHealthScore(score) {
    if (score >= 80) return 'minimal';
    if (score >= 55) return 'mild';
    if (score >= 30) return 'moderate';
    return 'severe';
}

function buildReportCardHtml(report) {
    if (report.status !== 'ok') {
        return `
            <div class="report-warning">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;margin-top:2px;">
                    <path d="M12 9v4m0 4h.01M10.29 3.86l-8.18 14.18A1.5 1.5 0 0 0 3.5 20.5h17a1.5 1.5 0 0 0 1.39-2.46L13.71 3.86a1.5 1.5 0 0 0-2.42 0z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>${report.message || 'This analysis could not be completed.'}</span>
            </div>
        `;
    }

    const score = Math.round(report.overall_skin_health_score);
    const overallSeverity = severityForHealthScore(score);

    const metricsHtml = METRIC_ORDER.map(function(key) {
        const m = report.metrics[key];
        if (!m) return '';
        return `
            <div class="report-metric-item">
                <div class="report-metric-head">
                    <span class="report-metric-name">${m.label}</span>
                    <span class="severity-badge severity-${m.severity}">${m.severity}</span>
                </div>
                <div class="report-metric-bar-track">
                    <div class="report-metric-bar-fill bar-severity-${m.severity}" style="width: ${m.score}%;"></div>
                </div>
            </div>
        `;
    }).join('');

    const imagesHtml = (report.images && report.images.length)
        ? `<div class="report-images-grid">${report.images.map(function(url) {
              return `<img class="report-image-thumb" src="${url}" alt="Uploaded photo">`;
          }).join('')}</div>`
        : '';

    return `
        <div class="report-card">
            <div class="report-score-row">
                <div class="report-score-circle circle-severity-${overallSeverity}">
                    <span class="report-score-value">${score}</span>
                    <span class="report-score-unit">/ 100</span>
                </div>
                <div class="report-score-meta">
                    <span class="report-score-label">Overall Skin Health</span>
                    <span class="report-score-date">${report.images_analyzed} image(s) analyzed &middot; ${formatDate(report.created_at)}</span>
                </div>
            </div>
            <div class="report-metrics-grid">${metricsHtml}</div>
            ${imagesHtml}
        </div>
    `;
}
