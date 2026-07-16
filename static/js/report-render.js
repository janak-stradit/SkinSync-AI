/* Shared report-rendering helpers, used by app.js (post-upload card) and
   report_detail.js (standalone report page). Must be loaded before both. */

const METRIC_ORDER = ['acne', 'pimple', 'dark_spots', 'redness', 'dryness', 'wrinkles', 'pores'];

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

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function humanizeFieldKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, function(letter) { return letter.toUpperCase(); });
}

function renderProfileBlock(title, data) {
    if (!data) return '';
    const rows = Object.entries(data)
        .filter(function([key, value]) { return value !== null && value !== undefined && value !== ''; })
        .map(function([key, value]) {
            if (Array.isArray(value)) {
                value = value.join(', ');
            }
            return `
                <div class="report-intake-row">
                    <span class="report-intake-key">${humanizeFieldKey(key)}</span>
                    <span class="report-intake-value">${escapeHtml(value)}</span>
                </div>
            `;
        }).join('');

    if (!rows) {
        return '';
    }

    return `
        <div class="report-intake-block">
            <h4>${escapeHtml(title)}</h4>
            ${rows}
        </div>
    `;
}

const STAGE_ORDER = [
    { key: 'face_detection', detail: function(s) {
        return `${s.images_with_face} of ${s.images_total} image(s) had a detectable face`;
    } },
    { key: 'alignment', detail: function(s) {
        return `${s.images_aligned} of ${s.images_processed} image(s) eye-aligned for a straight crop`;
    } },
    { key: 'segmentation', detail: function(s) {
        const cov = s.avg_skin_coverage_pct != null ? `${s.avg_skin_coverage_pct}%` : 'n/a';
        return `Average detected skin coverage: ${cov}`;
    } },
    { key: 'preprocessing', detail: function(s) {
        return `${s.images_processed} image(s) processed — ${s.techniques.join(', ')}`;
    } },
    { key: 'feature_extraction', detail: function(s) {
        return `${s.images_analyzed} image(s) analyzed for acne, redness, dryness, wrinkles and pores`;
    } },
    { key: 'scoring', detail: function(s) {
        return `Final metric scores computed from ${s.images_used} image(s)`;
    } },
];

function buildStepsHtml(stageDetails) {
    if (!stageDetails) return '';

    const items = STAGE_ORDER.map(function(step, i) {
        const s = stageDetails[step.key];
        if (!s) return '';
        return `
            <div class="report-step-item">
                <div class="report-step-marker">${i + 1}</div>
                <div class="report-step-body">
                    <span class="report-step-name">${escapeHtml(s.label)}</span>
                    <span class="report-step-detail">${escapeHtml(step.detail(s))}</span>
                </div>
            </div>
        `;
    }).join('');

    return `
        <div class="report-steps">
            <h3 class="report-steps-title">Analysis Steps</h3>
            <div class="report-steps-list">${items}</div>
        </div>
    `;
}

function buildImageResultsHtml(stageDetails) {
    const items = stageDetails?.image_results || [];
    if (!items.length) return '';

    const rows = items.map(function(item, index) {
        const statusClass = item.status === 'ok' ? 'is-ok' : 'is-failed';
        const viewLabel = item.view === 'profile_left' ? 'Left profile'
            : item.view === 'profile_right' ? 'Right profile'
            : 'Front view';
        const coverage = typeof item.skin_coverage === 'number'
            ? ` · skin coverage ${(item.skin_coverage * 100).toFixed(1)}%`
            : '';
        return `
            <div class="report-image-review-row ${statusClass}">
                <div class="report-image-review-index">${index + 1}</div>
                <div class="report-image-review-body">
                    <span class="report-image-review-title">${escapeHtml(viewLabel)}</span>
                    <span class="report-image-review-detail">${escapeHtml(item.reason || 'No details available.')}${coverage}</span>
                </div>
            </div>
        `;
    }).join('');

    return `
        <div class="report-image-review">
            <h3 class="report-steps-title">Image Review</h3>
            <div class="report-image-review-list">${rows}</div>
        </div>
    `;
}

function buildAiAnalysisHtml(report) {
    const hasCached = Boolean(report.ai_analysis);
    const cached = hasCached
        ? `<div class="report-ai-result">${escapeHtml(report.ai_analysis).replace(/\n/g, '<br>')}</div>`
        : `<div class="report-ai-empty">Your AI skin advisor summary will appear here after you generate it.</div>`;

    const actionLabel = hasCached ? 'Refresh Treatment and Recommendation' : 'Treatment and Recommendation';
    const buttonHtml = report.id
        ? `<button type="button" class="btn-primary report-ai-btn">${actionLabel}</button>`
        : '';

    return `
        <div class="report-ai-section" data-report-id="${report.id}">
            <div class="report-ai-head">
                <div>
                    <div class="report-ai-kicker">Treatment Plan</div>
                    <h4>Clinical recommendation and care guidance</h4>
                </div>
            </div>
            <div class="report-ai-error d-none"></div>
            ${cached}
            <div class="report-action-row report-ai-action-row">
                ${buttonHtml}
            </div>
        </div>
    `;
}

$(document).on('click', '.report-ai-btn', function() {
    const $btn = $(this);
    const $section = $btn.closest('.report-ai-section');
    const reportId = $section.data('report-id');
    const token = localStorage.getItem('access_token');
    const $error = $section.find('.report-ai-error').addClass('d-none').text('');

    $btn.addClass('is-loading').prop('disabled', true);

    $.ajax({
        url: `/api/profile/reports/${reportId}/ai-analysis`,
        type: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        success: function(res) {
            $section.find('.report-ai-empty').remove();
            $section.find('.report-ai-result').remove();
            $section.append(`<div class="report-ai-result">${escapeHtml(res.ai_analysis).replace(/\n/g, '<br>')}</div>`);
            $btn.text('Refresh Treatment and Recommendation');
        },
        error: function(err) {
            $error.removeClass('d-none').text(err.responseJSON?.msg || 'AI analysis failed. Please try again.');
        },
        complete: function() {
            $btn.removeClass('is-loading').prop('disabled', false);
        }
    });
});

const INTAKE_LABEL_MAPS = {
    skin_type: { oily: 'Oily', dry: 'Dry', combination: 'Combination', normal: 'Normal', sensitive: 'Sensitive' },
    sensitivity_level: { low: 'Low', medium: 'Medium', high: 'High' },
    skin_tone: {
        fair: 'Type I - II (Fair / Light)', medium: 'Type III (Medium)', olive: 'Type IV (Olive)',
        brown: 'Type V (Brown)', dark: 'Type VI (Dark)',
    },
    skin_concerns: {
        acne: 'Acne Vulgaris / Breakouts', blackheads: 'Comedones (Blackheads)', pigmentation: 'Hyperpigmentation',
        wrinkles: 'Fine Lines / Wrinkles', dryness: 'Severe Dryness / Eczema', none: 'No major concerns',
    },
    acne_level: { none: 'None', mild: 'Mild', moderate: 'Moderate', severe: 'Severe / Cystic' },
    pigmentation_level: { none: 'None', mild: 'Mild', moderate: 'Moderate', severe: 'Severe' },
    pore_size: { small: 'Small (Invisible)', medium: 'Medium', large: 'Large (Prominent)' },
    under_eye_issue: {
        none: 'Normal', dark_circles: 'Periorbital Hyperpigmentation (Dark Circles)',
        puffiness: 'Periorbital Edema (Puffiness)', wrinkles: 'Periorbital Rhytides (Wrinkles)',
    },
    lip_condition: { normal: 'Normal', dry: 'Dry / Chapped', pigmented: 'Pigmented' },
    seasonal_skin_changes: {
        none: 'Stable year-round', dry_winter: 'Increased dryness in Winter',
        oily_summer: 'Increased sebum production in Summer', both: 'Reactive to both extremes',
    },
    stress_level: { low: 'Low', medium: 'Moderate', high: 'High' },
    exercise_frequency: { none: 'None', '1-2': '1-2 days/week', '3-4': '3-4 days/week', '5+': '5+ days/week' },
    screen_time: { low: 'Under 2 hours', medium: '2 - 6 hours', high: 'Over 6 hours' },
    sunscreen_usage: { never: 'Never', rarely: 'Rarely (Only when sunny/outdoors)', sometimes: 'Sometimes', always: 'Always (Daily)' },
    face_washing_frequency: { '1': 'Once a day', '2': 'Twice a day', '3+': 'More than twice a day', rarely: 'Rarely' },
    makeup_usage: { never: 'Never', occasionally: 'Occasionally', daily_light: 'Daily (Light)', daily_heavy: 'Daily (Heavy/Full Face)' },
    pollution_exposure: { low: 'Low (Rural / Clean air)', medium: 'Medium (Suburban)', high: 'High (Urban / Industrial)' },
    occupation_type: {
        indoor: 'Indoor / Desk Job', outdoor: 'Outdoor / Field Work',
        mixed: 'Mixed (Indoor & Outdoor)', active: 'Highly Active (Fitness, manual labor)',
    },
    has_known_allergy: { yes: 'Yes', no: 'No' },
    allergy_type: {
        food: 'Food Allergy', environmental: 'Environmental (Dust, Pollen, etc.)', skincare: 'Skincare Ingredients',
        medication: 'Medication', multiple: 'Multiple Types',
    },
    reaction_symptoms: {
        redness: 'Redness / Erythema', itching: 'Itching / Pruritus', swelling: 'Swelling / Edema',
        hives: 'Hives / Urticaria', breakouts: 'Breakouts / Acne',
    },
    reaction_severity: {
        mild: 'Mild (Fades quickly)', moderate: 'Moderate (Requires basic care)', severe: 'Severe (Requires medical attention)',
    },
    visited_dermatologist: { yes: 'Yes', no: 'No' },
    taking_medication: { yes: 'Yes', no: 'No' },
};

function intakeField(label, key, rawValue, unit) {
    const map = INTAKE_LABEL_MAPS[key];
    const hasValue = rawValue !== null && rawValue !== undefined && rawValue !== '';
    const display = hasValue ? escapeHtml((map && map[rawValue]) || rawValue) + (unit ? ` ${unit}` : '') : 'Not provided';
    return `
        <div class="intake-field">
            <span class="intake-field-label">${label}</span>
            <span class="intake-field-value${hasValue ? '' : ' intake-field-empty'}">${display}</span>
        </div>
    `;
}

function intakeSection(title, innerHtml, sectionKey) {
    return `
        <div class="intake-section">
            <button type="button" class="intake-section-toggle" data-target="${sectionKey}" aria-expanded="false">
                <span>${title}</span>
                <span class="intake-section-caret">⌄</span>
            </button>
            <div class="intake-section-panel d-none" data-panel="${sectionKey}">
                <div class="intake-fields-grid">${innerHtml}</div>
            </div>
        </div>
    `;
}

function buildIntakeHtml(intake) {
    const skin = intake && intake.skin_profile;
    const lifestyle = intake && intake.lifestyle_profile;
    const allergy = intake && intake.allergy_profile;
    const diet = intake && intake.diet_profile;

    const skinHtml = skin ? [
        intakeField('Skin Type', 'skin_type', skin.skin_type),
        intakeField('Sensitivity Level', 'sensitivity_level', skin.sensitivity_level),
        intakeField('Skin Tone', 'skin_tone', skin.skin_tone),
        intakeField('Primary Skin Concerns', 'skin_concerns', skin.skin_concerns),
        intakeField('Acne Severity', 'acne_level', skin.acne_level),
        intakeField('Pigmentation Level', 'pigmentation_level', skin.pigmentation_level),
        intakeField('Pore Size', 'pore_size', skin.pore_size),
        intakeField('Under Eye Area', 'under_eye_issue', skin.under_eye_issue),
        intakeField('Lip Condition', 'lip_condition', skin.lip_condition),
        intakeField('Seasonal Reactivity', 'seasonal_skin_changes', skin.seasonal_skin_changes),
    ].join('') : '<p class="intake-empty-msg">Not completed yet.</p>';

    const lifestyleHtml = lifestyle ? [
        intakeField('Sleep Duration', 'sleep_hours', lifestyle.sleep_hours, 'hrs'),
        intakeField('Stress Level', 'stress_level', lifestyle.stress_level),
        intakeField('Exercise Frequency', 'exercise_frequency', lifestyle.exercise_frequency),
        intakeField('Screen Time', 'screen_time', lifestyle.screen_time),
        intakeField('Sunscreen Usage', 'sunscreen_usage', lifestyle.sunscreen_usage),
        intakeField('Face Washing', 'face_washing_frequency', lifestyle.face_washing_frequency),
        intakeField('Makeup Usage', 'makeup_usage', lifestyle.makeup_usage),
        intakeField('Pollution Exposure', 'pollution_exposure', lifestyle.pollution_exposure),
        intakeField('Occupation Type', 'occupation_type', lifestyle.occupation_type),
    ].join('') : '<p class="intake-empty-msg">Not completed yet.</p>';

    const allergyHtml = allergy ? [
        intakeField('Known Allergies', 'has_known_allergy', allergy.has_known_allergy),
        intakeField('Allergy Type', 'allergy_type', allergy.allergy_type),
        intakeField('Reactive Ingredients', 'reactive_ingredients', allergy.reactive_ingredients),
        intakeField('Reaction Symptoms', 'reaction_symptoms', allergy.reaction_symptoms),
        intakeField('Reaction Severity', 'reaction_severity', allergy.reaction_severity),
        intakeField('Visited Dermatologist', 'visited_dermatologist', allergy.visited_dermatologist),
        intakeField('Taking Medication', 'taking_medication', allergy.taking_medication),
        intakeField('Additional Info', 'additional_allergy_info', allergy.additional_allergy_info),
    ].join('') : '<p class="intake-empty-msg">Not completed yet.</p>';

    const dietHtml = diet ? [
        intakeField('Hydration Volume', 'water_intake_liters', diet.water_intake_liters, 'L/day'),
        intakeField('Fruits & Vegetable Intake', 'fruits_veggies_intake', diet.fruits_veggies_intake),
        intakeField('Fast Food Frequency', 'fast_food_freq', diet.fast_food_freq),
        intakeField('Sugary Food Consumption', 'sugar_consumption', diet.sugar_consumption),
        intakeField('Alcohol / Smoking', 'alcohol_smoking', diet.alcohol_smoking),
        intakeField('Tea / Coffee Intake', 'tea_coffee_intake', diet.tea_coffee_intake),
    ].join('') : '<p class="intake-empty-msg">Not completed yet.</p>';

    return `
        <div class="report-intake-panel">
            <h3 class="report-intake-heading">Clinical Intake</h3>
            ${intakeSection('Skin Profile', skinHtml, 'skin')}
            ${intakeSection('Lifestyle', lifestyleHtml, 'lifestyle')}
            ${intakeSection('Allergies', allergyHtml, 'allergies')}
            ${intakeSection('Diet &amp; Habits', dietHtml, 'diet')}
        </div>
    `;
}

$(document).on('click', '.intake-section-toggle', function() {
    const key = $(this).data('target');
    const $panel = $(`.intake-section-panel[data-panel="${key}"]`);
    const expanded = $(this).attr('aria-expanded') === 'true';
    $(this).attr('aria-expanded', String(!expanded));
    $panel.toggleClass('d-none', expanded);
});

$(document).on('click', '.report-summary-toggle', function() {
    const expanded = $(this).attr('aria-expanded') === 'true';
    $(this).attr('aria-expanded', String(!expanded));
    $(this).closest('.report-summary-section').find('.report-summary-panel').toggleClass('d-none', expanded);
});

$(document).on('click', '.report-photo-toggle', function() {
    const expanded = $(this).attr('aria-expanded') === 'true';
    $(this).attr('aria-expanded', String(!expanded));
    $(this).closest('.report-photo-section').find('.report-photo-panel').toggleClass('d-none', expanded);
});

$(document).on('click', '.report-metric-toggle', function() {
    const key = $(this).data('target');
    const expanded = $(this).attr('aria-expanded') === 'true';
    $(this).attr('aria-expanded', String(!expanded));
    $(`.report-metric-details[data-panel="${key}"]`).toggleClass('d-none', expanded);
});

function buildReportPageHtml(report) {
    return `
        <div class="report-page-grid">
            <div class="report-page-card">${buildReportCardHtml(report)}</div>
        </div>
    `;
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
        const detail = report.stage_details?.metric_details?.[key] || {};
        const raw = detail.raw || {};
        const detailText = detail.detail || `Score based on ${m.label.toLowerCase()} features.`;
        return `
            <div class="report-metric-item">
                <button type="button" class="report-metric-toggle" data-target="${key}" aria-expanded="false">
                    <div class="report-metric-head">
                        <span class="report-metric-name">${m.label}</span>
                        <span class="severity-badge severity-${m.severity}">${m.severity}</span>
                    </div>
                    <div class="report-metric-bar-track">
                        <div class="report-metric-bar-fill bar-severity-${m.severity}" style="width: ${m.score}%;"></div>
                    </div>
                </button>
                <div class="report-metric-details d-none" data-panel="${key}">
                    <div class="report-metric-detail-copy">${escapeHtml(detailText)}</div>
                    ${Object.keys(raw).length ? `<div class="report-metric-detail-raw">${escapeHtml(JSON.stringify(raw))}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');

    const imagesHtml = (report.images && report.images.length)
        ? `
            <div class="report-photo-section">
                <button type="button" class="report-photo-toggle" aria-expanded="false">
                    <span>Photography</span>
                    <span class="intake-section-caret">⌄</span>
                </button>
                <div class="report-photo-panel d-none">
                    <div class="report-images-grid">${report.images.map(function(url) {
                        return `<img class="report-image-thumb" src="${url}" alt="Uploaded photo">`;
                    }).join('')}</div>
                </div>
            </div>
        `
        : '';

    const patientSnapshotHtml = `
        <div class="report-intake-section report-summary-section">
            <button type="button" class="report-summary-toggle" aria-expanded="false">
                <span>Patient Summary</span>
                <span class="intake-section-caret">⌄</span>
            </button>
            <div class="report-summary-panel d-none">
                <div class="report-intake-grid">
                    <div class="report-intake-block">
                        <h4>Assessment Overview</h4>
                        <div class="report-intake-row">
                            <span class="report-intake-key">Usable Images</span>
                            <span class="report-intake-value">${report.images_analyzed}</span>
                        </div>
                        <div class="report-intake-row">
                            <span class="report-intake-key">Images Skipped</span>
                            <span class="report-intake-value">${report.images_skipped || 0}</span>
                        </div>
                        <div class="report-intake-row">
                            <span class="report-intake-key">Assessment Date</span>
                            <span class="report-intake-value">${formatDate(report.created_at)}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    const intakeSummary = report.intake_summary || {};
    const intakeHtml = intakeSummary.skin_profile || intakeSummary.lifestyle_profile || intakeSummary.allergy_profile || intakeSummary.diet_profile
        ? `
            <div class="report-intake-section">
                <div class="report-section-heading">Clinical Intake Summary</div>
                <div class="report-intake-grid">
                    ${renderProfileBlock('Skin Profile', intakeSummary.skin_profile)}
                    ${renderProfileBlock('Lifestyle Profile', intakeSummary.lifestyle_profile)}
                    ${renderProfileBlock('Allergy Profile', intakeSummary.allergy_profile)}
                    ${renderProfileBlock('Diet Profile', intakeSummary.diet_profile)}
                </div>
            </div>
        `
        : '';

    return `
        <div class="report-card">
            <div class="report-report-title">
                <div class="report-page-kicker">Medical Skin Report</div>
                <h2>${report.username ? `Patient assessment for ${escapeHtml(report.username)}` : 'Patient assessment with structured clinical findings'}</h2>
                <p>All uploaded inputs and image-derived scores are summarized below for review and future recommendations.</p>
            </div>
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
            ${patientSnapshotHtml}
            <div class="report-metrics-grid">${metricsHtml}</div>
            ${imagesHtml}
            ${intakeHtml}
            ${buildAiAnalysisHtml(report)}
        </div>
    `;
}
