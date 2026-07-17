$(document).ready(function() {
    const $container = $('#treatment-page-container');
    const token = localStorage.getItem('access_token');
    let report = null;

    function showState(title, message, showLoginLink) {
        $container.html(`
            <div class="report-page-card">
                <div class="report-page-state">
                    <h2>${escapeHtml(title)}</h2>
                    <p>${escapeHtml(message)}</p>
                    ${showLoginLink ? '<a href="/" class="btn-primary">Go to Login</a>' : ''}
                </div>
            </div>
        `);
    }

    function showLoading() {
        $container.html(`
            <div class="report-page-card">
                <div class="report-page-state">
                    <div class="report-page-spinner"></div>
                    <p>Preparing your personalized treatment plan&hellip;</p>
                </div>
            </div>
        `);
    }

    function generateTreatment() {
        showLoading();
        $.ajax({
            url: `/api/profile/reports/${REPORT_ID}/ai-analysis`,
            type: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            success: function(response) {
                $container.html(`
                    <div class="report-page-card treatment-page-card">
                        ${buildAiAnalysisResultHtml(response.ai_analysis, report)}
                        <div class="report-action-row treatment-refresh-row">
                            <button type="button" class="btn-primary" id="refresh-treatment-btn">Refresh Recommendations</button>
                        </div>
                    </div>
                `);
            },
            error: function(error) {
                showState('Treatment plan unavailable', error.responseJSON?.msg || 'We could not prepare the treatment plan. Please try again.', false);
            }
        });
    }

    if (!token) {
        showState('Sign in required', 'Log in to view your treatment and recommendations.', true);
        return;
    }

    $.ajax({
        url: `/api/profile/reports/${REPORT_ID}`,
        type: 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
        success: function(response) {
            report = response;
            generateTreatment();
        },
        error: function(error) {
            showState('Report not found', error.responseJSON?.msg || 'This report does not exist or you do not have access to it.', error.status === 401);
        }
    });

    $(document).on('click', '#refresh-treatment-btn', generateTreatment);
});
