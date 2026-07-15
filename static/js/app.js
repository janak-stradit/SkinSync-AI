$(document).ready(function() {

    const API_URL = '/api';
    let currentStep = 1;
    const totalSteps = 5;
    let selectedFiles = [];

    // ----- Toasts -----

    function showToast(message, type) {
        const $toast = $(`<div class="app-toast toast-${type || 'info'}">${message}</div>`);
        $('#toast-stack').append($toast);
        setTimeout(function() {
            $toast.addClass('toast-out');
            setTimeout(function() { $toast.remove(); }, 200);
        }, 3800);
    }

    // ----- Button loading state -----

    function setButtonLoading($btn, isLoading) {
        $btn.toggleClass('is-loading', isLoading).prop('disabled', isLoading);
    }

    // ----- Session bootstrap -----

    function enterWizard() {
        $('#auth-container').addClass('d-none');
        $('#stepper-container').removeClass('d-none');
        $('#logout-btn').removeClass('d-none');
        $('#history-btn').removeClass('d-none');
        $('#header-status').text('Clinical Assessment In Progress');
    }

    // Always begin with a fresh login when the application is opened.
    localStorage.removeItem('access_token');

    $('#logout-btn').click(function() {
        localStorage.removeItem('access_token');
        window.location.reload();
    });

    // ----- Auth Logic -----

    $('#register-form').submit(function(e) {
        e.preventDefault();
        const $btn = $(this).find('button[type="submit"]');
        const data = {
            username: $('#reg-username').val(),
            email: $('#reg-email').val(),
            password: $('#reg-password').val()
        };

        setButtonLoading($btn, true);
        $.ajax({
            url: `${API_URL}/auth/register`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(res) {
                showToast('Registration successful. Please log in.', 'success');
                $('#login-tab').tab('show');
            },
            error: function(err) {
                showToast(err.responseJSON?.msg || 'Registration failed', 'error');
            },
            complete: function() { setButtonLoading($btn, false); }
        });
    });

    $('#login-form').submit(function(e) {
        e.preventDefault();
        const $btn = $(this).find('button[type="submit"]');
        const data = {
            username: $('#login-username').val(),
            password: $('#login-password').val()
        };

        setButtonLoading($btn, true);
        $.ajax({
            url: `${API_URL}/auth/login`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(res) {
                localStorage.setItem('access_token', res.access_token);
                window.history.replaceState({}, '', '/');
                enterWizard();
            },
            error: function(err) {
                showToast(err.responseJSON?.msg || 'Login failed', 'error');
            },
            complete: function() { setButtonLoading($btn, false); }
        });
    });

    $('.password-toggle').on('click', function() {
        const $input = $($(this).attr('data-target'));
        const showingPassword = $input.attr('type') === 'text';
        $input.attr('type', showingPassword ? 'password' : 'text');
        $(this).attr('aria-label', showingPassword ? 'Show password' : 'Hide password');
        $(this).toggleClass('is-visible', !showingPassword);
    });

    // ----- Stepper Logic -----

    function getAuthHeaders() {
        return {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        };
    }

    function updateProgress(step) {
        const percent = Math.round((step / totalSteps) * 100);
        $('#form-progress').css('width', `${percent}%`);
        $('#progress-percent').text(percent);
    }

    function updateStepList(step) {
        $('.step-list-item').each(function() {
            const itemStep = parseInt($(this).data('step'));
            $(this).removeClass('active completed');
            if (itemStep < step) {
                $(this).addClass('completed');
            } else if (itemStep === step) {
                $(this).addClass('active');
            }
        });
    }

    function showStep(step) {
        $('.step-content').addClass('d-none').removeClass('active');
        $(`#step-${step}`).removeClass('d-none').addClass('active fade-in');
        updateProgress(step);
        updateStepList(step);
        $('.wizard-panel')[0]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    $('.btn-prev').click(function() {
        if (currentStep > 1) {
            if (currentStep === 5) stopCamera();
            currentStep--;
            showStep(currentStep);
        }
    });

    function submitStep(formSelector, url, buildData, nextStep) {
        $(formSelector).submit(function(e) {
            e.preventDefault();
            const $btn = $(this).find('button[type="submit"]');
            const data = buildData();

            setButtonLoading($btn, true);
            $.ajax({
                url: `${API_URL}${url}`,
                type: 'POST',
                contentType: 'application/json',
                headers: getAuthHeaders(),
                data: JSON.stringify(data),
                success: function() {
                    currentStep = nextStep;
                    showStep(currentStep);
                },
                error: function(err) {
                    showToast(err.responseJSON?.msg || 'Error saving profile', 'error');
                },
                complete: function() { setButtonLoading($btn, false); }
            });
        });
    }

    // Step 1
    submitStep('#form-step-1', '/profile/skin', function() {
        function checkboxValues(name) {
            return $(`input[name="${name}"]:checked`).map(function(){ return this.value; }).get();
        }

        return {
            skin_type: $('#skin_type').val(),
            skin_tone: $('#skin_tone').val(),
            skin_concerns: checkboxValues('skin_concerns[]'),
            under_eye_issue: checkboxValues('under_eye_issue[]'),
            lip_condition: checkboxValues('lip_condition[]'),
            sensitivity_level: $('#sensitivity_level').val(),
            additional_concern: $('#additional_concern').val()
        };
    }, 2);

    // Step 2
    submitStep('#form-step-2', '/profile/lifestyle', function() {
        function checkboxValues(name) { return $(`input[name="${name}"]:checked`).map(function(){ return this.value; }).get(); }
        return {
            sleep_hours: parseInt($('#sleep_hours').val()),
            stress_level: $('#stress_level').val(),
            alcohol_smoking: $('#alcohol_smoking').val(),
            medical_conditions: checkboxValues('medical_conditions[]'),
            medical_conditions_other: $('#medical_conditions_other').val()
        };
    }, 3);

    // Step 3
    $('#has_known_allergy').change(function() {
        if ($(this).val() === 'yes') {
            $('#allergy_details_section').removeClass('d-none').addClass('fade-in');
        } else {
            $('#allergy_details_section').addClass('d-none').removeClass('fade-in');
        }
    });

    submitStep('#form-step-3', '/profile/allergy', function() {
        function checkboxValues(name) { return $(`input[name="${name}"]:checked`).map(function(){ return this.value; }).get(); }
        return {
            has_known_allergy: $('#has_known_allergy').val(),
            allergy_type: checkboxValues('allergy_type[]'),
            allergy_type_other: $('#allergy_type_other').val(),
            reactive_ingredients: $('#reactive_ingredients').val(),
            reaction_symptoms: $('#reaction_symptoms').val(),
            reaction_severity: $('#reaction_severity').val(),
            visited_dermatologist: $('#visited_dermatologist').val(),
            taking_medication: $('#taking_medication').val(),
            additional_allergy_info: $('#additional_allergy_info').val(),
            skin_medication: $('#skin_medication').val(),
            recent_treatment: $('#recent_treatment').val(),
            recent_treatment_other: $('#recent_treatment_other').val()
        };
    }, 4);

    // Step 4
    submitStep('#form-step-4', '/profile/diet', function() {
        return {
            water_intake_liters: parseFloat($('#water_intake').val()),
            sugar_consumption: $('#sugar_consumption').val(),
            fruits_veggies_intake: $('#fruits_veggies_intake').val(),
            fast_food_freq: $('#fast_food_freq').val(),
            alcohol_smoking: $('#alcohol_smoking').val(),
            tea_coffee_intake: $('#tea_coffee_intake').val(),
            supplements: $('#supplements').val(),
            supplements_text: $('#supplements_text').val()
        };
    }, 5);

    // Step 5 - Images
    const $dropZone = $('#drop-zone');
    const $fileInput = $('#images');
    const $previewGrid = $('#image-preview-grid');
    const $cameraPanel = $('#camera-panel');
    const cameraVideo = document.getElementById('camera-video');
    const cameraCanvas = document.getElementById('camera-canvas');
    let cameraStream = null;

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(function(track) { track.stop(); });
            cameraStream = null;
        }
        if (cameraVideo) cameraVideo.srcObject = null;
        $cameraPanel.addClass('d-none');
        $('#open-camera-btn').prop('disabled', false);
    }

    $('#open-camera-btn').on('click', async function() {
        if (!navigator.mediaDevices?.getUserMedia) {
            showToast('Camera access is not supported by this browser.', 'error');
            return;
        }
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 960 } },
                audio: false
            });
            cameraVideo.srcObject = cameraStream;
            $cameraPanel.removeClass('d-none').addClass('fade-in');
            $(this).prop('disabled', true);
            $cameraPanel[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        } catch (error) {
            showToast(error.name === 'NotAllowedError'
                ? 'Camera permission was denied. Please allow camera access and try again.'
                : 'Could not open the camera. You can still select images from your device.', 'error');
            stopCamera();
        }
    });

    $('#close-camera-btn').on('click', stopCamera);

    $('#capture-photo-btn').on('click', function() {
        if (!cameraStream || !cameraVideo.videoWidth) {
            showToast('The camera is still starting. Please try again.', 'info');
            return;
        }
        cameraCanvas.width = cameraVideo.videoWidth;
        cameraCanvas.height = cameraVideo.videoHeight;
        const context = cameraCanvas.getContext('2d');
        context.drawImage(cameraVideo, 0, 0, cameraCanvas.width, cameraCanvas.height);
        cameraCanvas.toBlob(function(blob) {
            if (!blob) {
                showToast('Could not capture the photo. Please try again.', 'error');
                return;
            }
            const file = new File([blob], `camera-${Date.now()}.jpg`, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });
            addFiles([file]);
            const views = ['front view', 'left-side view', 'right-side view'];
            const nextView = views[Math.min(selectedFiles.length, 2)];
            $('#camera-angle-hint').text(selectedFiles.length >= 3
                ? 'Minimum complete. Add more photos or submit your profile.'
                : `Next: capture the ${nextView}.`);
            showToast('Photo captured successfully.', 'success');
        }, 'image/jpeg', 0.92);
    });

    function syncFileInput() {
        const dataTransfer = new DataTransfer();
        selectedFiles.forEach(function(file) { dataTransfer.items.add(file); });
        $fileInput[0].files = dataTransfer.files;
    }

    function renderPreviews() {
        $previewGrid.empty();
        selectedFiles.forEach(function(file, index) {
            const url = URL.createObjectURL(file);
            const $item = $(`
                <div class="image-preview-item">
                    <img src="${url}" alt="Preview">
                    <button type="button" class="image-preview-remove" data-index="${index}">&times;</button>
                </div>
            `);
            $previewGrid.append($item);
        });

        if (selectedFiles.length === 0) {
            $('#file-count').text('Drag & drop, or click to browse. Minimum of 3 images required.');
        } else if (selectedFiles.length < 3) {
            $('#file-count').text(`${selectedFiles.length} image(s) selected — add at least ${3 - selectedFiles.length} more.`);
        } else {
            $('#file-count').text(`${selectedFiles.length} image(s) selected.`);
        }
    }

    function addFiles(fileList) {
        Array.from(fileList).forEach(function(file) {
            const alreadySelected = selectedFiles.some(function(selected) {
                return selected.name === file.name
                    && selected.size === file.size
                    && selected.lastModified === file.lastModified;
            });
            if (file.type.startsWith('image/') && !alreadySelected) {
                selectedFiles.push(file);
            }
        });
        syncFileInput();
        renderPreviews();
    }

    $fileInput.on('change', function() {
        addFiles(this.files);
    });

    $previewGrid.on('click', '.image-preview-remove', function() {
        const index = parseInt($(this).data('index'));
        selectedFiles.splice(index, 1);
        syncFileInput();
        renderPreviews();
    });

    $dropZone.on('dragover', function(e) {
        e.preventDefault();
        $dropZone.addClass('is-dragover');
    });

    $dropZone.on('dragleave drop', function() {
        $dropZone.removeClass('is-dragover');
    });

    $dropZone.on('drop', function(e) {
        e.preventDefault();
        const dt = e.originalEvent.dataTransfer;
        if (dt && dt.files) {
            addFiles(dt.files);
        }
    });

    $('#form-step-5').submit(function(e) {
        e.preventDefault();
        const $btn = $(this).find('button[type="submit"]');

        if (selectedFiles.length < 3) {
            showToast('Please select at least 3 images.', 'error');
            return;
        }

        const formData = new FormData();
        selectedFiles.forEach(function(file) {
            formData.append('images', file);
        });

        setButtonLoading($btn, true);
        stopCamera();
        $.ajax({
            url: `${API_URL}/profile/upload_images`,
            type: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            data: formData,
            processData: false,
            contentType: false,
            success: function(res) {
                const reportStatus = res.report?.status;
                $('.step-content').addClass('d-none').removeClass('active');
                $('#step-success').removeClass('d-none').addClass('active fade-in');
                $('#form-progress').css('width', `100%`);
                $('#progress-percent').text(100);
                $('.step-list-item').removeClass('active').addClass('completed');
                $('#header-status').text(reportStatus === 'ok' ? 'Assessment Complete' : 'Assessment Incomplete');
                if (res.report) {
                    $('#report-container').html(buildReportCardHtml(res.report));
                }
                // Do not retain one assessment's photos for a later submission/user.
                selectedFiles = [];
                syncFileInput();
                renderPreviews();
            },
            error: function(err) {
                showToast(err.responseJSON?.msg || 'Error uploading images', 'error');
            },
            complete: function() { setButtonLoading($btn, false); }
        });
    });

    // ----- History -----

    function buildHistoryListItemHtml(r) {
        if (r.status !== 'ok') {
            return `
                <a href="/reports/${r.id}" target="_blank" rel="noopener noreferrer" class="history-list-item">
                    <div class="history-item-score is-warning">!</div>
                    <div class="history-item-info">
                        <span class="history-item-date">${formatDate(r.created_at)}</span>
                        <span class="history-item-sub">${r.message || 'Analysis failed'}</span>
                    </div>
                    <svg class="history-item-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </a>
            `;
        }
        const score = Math.round(r.overall_skin_health_score);
        const sev = severityForHealthScore(score);
        return `
            <a href="/reports/${r.id}" target="_blank" rel="noopener noreferrer" class="history-list-item">
                <div class="history-item-score circle-severity-${sev}">${score}</div>
                <div class="history-item-info">
                    <span class="history-item-date">${formatDate(r.created_at)}</span>
                    <span class="history-item-sub">${r.images_analyzed} image(s) analyzed</span>
                </div>
                <svg class="history-item-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </a>
        `;
    }

    function loadHistoryList() {
        $('#history-list').empty();
        $('#history-empty').addClass('d-none');
        $.ajax({
            url: `${API_URL}/profile/reports`,
            type: 'GET',
            headers: getAuthHeaders(),
            success: function(res) {
                const reports = res.reports || [];
                if (reports.length === 0) {
                    $('#history-empty').removeClass('d-none');
                    return;
                }
                reports.forEach(function(r) {
                    $('#history-list').append(buildHistoryListItemHtml(r));
                });
            },
            error: function(err) {
                showToast(err.responseJSON?.msg || 'Could not load history', 'error');
            }
        });
    }

    $('#history-btn').on('click', function() {
        loadHistoryList();
        const modalEl = document.getElementById('history-modal');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    });

});
