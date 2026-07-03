$(document).ready(function() {

    const API_URL = '/api';
    const $container = $('#report-page-container');
    const token = localStorage.getItem('access_token');

    function showState(title, message, showLoginLink) {
        const loginLink = showLoginLink
            ? `<a href="/" class="btn-primary">Go to Login</a>`
            : '';
        $container.html(`
            <div class="report-page-state">
                <h2>${title}</h2>
                <p>${message}</p>
                ${loginLink}
            </div>
        `);
    }

    if (!token) {
        showState('Sign in required', 'Log in to SkinSync AI to view this assessment report.', true);
        return;
    }

    $.ajax({
        url: `${API_URL}/profile/reports/${REPORT_ID}`,
        type: 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
        success: function(report) {
            document.title = `Report · ${formatDate(report.created_at)} - SkinSync AI`;
            $container.html(buildReportCardHtml(report));
        },
        error: function(err) {
            if (err.status === 401) {
                showState('Session expired', 'Please log in again to view this report.', true);
            } else {
                showState('Report not found', err.responseJSON?.msg || 'This report does not exist or you do not have access to it.', false);
            }
        }
    });

});
