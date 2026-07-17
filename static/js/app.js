$(document).ready(function() {

    const API_URL = '/api';
    let currentStep = 1;
    const totalSteps = 5;
    let selectedFiles = [];
    const WIZARD_STATE_KEY = 'skinsync_wizard_state';
    const WIZARD_STATE_BACKUP_KEY = 'skinsync_wizard_state_backup';
    const RETURN_TO_WIZARD_KEY = 'skinsync_return_to_wizard';

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
        const username = localStorage.getItem('skinsync_username');
        $('#header-greeting')
            .text(username ? `Welcome back, ${username}` : 'Welcome back')
            .removeClass('d-none');
        $('#header-status').text(username ? `Clinical Assessment In Progress · ${username}` : 'Clinical Assessment In Progress');
    }

    function hydrateWizardFromReturn() {
        if (sessionStorage.getItem(RETURN_TO_WIZARD_KEY) !== '1') return false;
        if (!localStorage.getItem('access_token')) {
            sessionStorage.removeItem(RETURN_TO_WIZARD_KEY);
            return false;
        }
        enterWizard();
        restoreWizardState();
        loadSavedIntakeFromServer(function() {
            showStep(currentStep);
            sessionStorage.removeItem(RETURN_TO_WIZARD_KEY);
        });
        return true;
    }

    if (!hydrateWizardFromReturn()) {
        // Always start fresh on project open.
        localStorage.removeItem('access_token');
        localStorage.removeItem('skinsync_username');
    }

    function restoreCheckboxes(name, values) {
        const valueSet = new Set((values || []).map(String));
        $(`input[name="${name}"]`).each(function() {
            this.checked = valueSet.has(this.value);
        });
    }

    function persistWizardState() {
        if (!localStorage.getItem('access_token')) return;
        const state = {
            currentStep: currentStep,
            skinProfile: {
                skin_type: $('#skin_type').val(),
                skin_tone: $('#skin_tone').val(),
                skin_concerns: $('input[name="skin_concerns[]"]:checked').map(function(){ return this.value; }).get(),
                under_eye_issue: $('input[name="under_eye_issue[]"]:checked').map(function(){ return this.value; }).get(),
                lip_condition: $('input[name="lip_condition[]"]:checked').map(function(){ return this.value; }).get(),
                sensitivity_level: $('#sensitivity_level').val(),
                additional_concern: $('#additional_concern').val()
            },
            lifestyleProfile: {
                sleep_hours: $('#sleep_hours').val(),
                stress_level: $('#stress_level').val(),
                alcohol_smoking: $('#alcohol_smoking').val(),
                medical_conditions: $('input[name="medical_conditions[]"]:checked').map(function(){ return this.value; }).get(),
                medical_conditions_other: $('#medical_conditions_other').val()
            },
            allergyProfile: {
                has_known_allergy: $('#has_known_allergy').val(),
                allergy_type: $('input[name="allergy_type[]"]:checked').map(function(){ return this.value; }).get(),
                allergy_type_other: $('#allergy_type_other').val(),
                reaction_symptoms: $('#reaction_symptoms').val(),
                reaction_severity: $('#reaction_severity').val(),
                visited_dermatologist: $('#visited_dermatologist').val(),
                taking_medication: $('#taking_medication').val(),
                additional_allergy_info: $('#additional_allergy_info').val(),
                skin_medication: $('#skin_medication').val(),
                recent_treatment: $('#recent_treatment').val(),
                recent_treatment_other: $('#recent_treatment_other').val()
            },
            dietProfile: {
                water_intake: $('#water_intake').val(),
                fruits_veggies_intake: $('#fruits_veggies_intake').val(),
                fast_food_freq: $('#fast_food_freq').val(),
                sugar_consumption: $('#sugar_consumption').val(),
                alcohol_smoking: $('#alcohol_smoking').val(),
                tea_coffee_intake: $('#tea_coffee_intake').val(),
                supplements: $('#supplements').val(),
                supplements_text: $('#supplements_text').val()
            }
        };
        const serialized = JSON.stringify(state);
        sessionStorage.setItem(WIZARD_STATE_KEY, serialized);
        localStorage.setItem(WIZARD_STATE_BACKUP_KEY, serialized);
    }

    function restoreWizardState() {
        const raw = sessionStorage.getItem(WIZARD_STATE_KEY) || localStorage.getItem(WIZARD_STATE_BACKUP_KEY);
        if (!raw) return false;
        try {
            const state = JSON.parse(raw);
            if (!state) return false;
            currentStep = state.currentStep || 1;

            if (state.skinProfile) {
                $('#skin_type').val(state.skinProfile.skin_type || '');
                $('#skin_tone').val(state.skinProfile.skin_tone || '');
                restoreCheckboxes('skin_concerns[]', state.skinProfile.skin_concerns);
                restoreCheckboxes('under_eye_issue[]', state.skinProfile.under_eye_issue);
                restoreCheckboxes('lip_condition[]', state.skinProfile.lip_condition);
                $('#sensitivity_level').val(state.skinProfile.sensitivity_level || '');
                $('#additional_concern').val(state.skinProfile.additional_concern || '');
            }
            if (state.lifestyleProfile) {
                $('#sleep_hours').val(state.lifestyleProfile.sleep_hours || '');
                $('#stress_level').val(state.lifestyleProfile.stress_level || '');
                $('#alcohol_smoking').val(state.lifestyleProfile.alcohol_smoking || '');
                restoreCheckboxes('medical_conditions[]', state.lifestyleProfile.medical_conditions);
                $('#medical_conditions_other').val(state.lifestyleProfile.medical_conditions_other || '');
            }
            if (state.allergyProfile) {
                $('#has_known_allergy').val(state.allergyProfile.has_known_allergy || '');
                restoreCheckboxes('allergy_type[]', state.allergyProfile.allergy_type);
                $('#allergy_type_other').val(state.allergyProfile.allergy_type_other || '');
                $('#reaction_symptoms').val(state.allergyProfile.reaction_symptoms || '');
                $('#reaction_severity').val(state.allergyProfile.reaction_severity || '');
                $('#visited_dermatologist').val(state.allergyProfile.visited_dermatologist || '');
                $('#taking_medication').val(state.allergyProfile.taking_medication || '');
                $('#additional_allergy_info').val(state.allergyProfile.additional_allergy_info || '');
                $('#skin_medication').val(state.allergyProfile.skin_medication || '');
                $('#recent_treatment').val(state.allergyProfile.recent_treatment || '');
                $('#recent_treatment_other').val(state.allergyProfile.recent_treatment_other || '');
            }
            if (state.dietProfile) {
                $('#water_intake').val(state.dietProfile.water_intake || '');
                $('#fruits_veggies_intake').val(state.dietProfile.fruits_veggies_intake || '');
                $('#fast_food_freq').val(state.dietProfile.fast_food_freq || '');
                $('#sugar_consumption').val(state.dietProfile.sugar_consumption || '');
                $('#alcohol_smoking').val(state.dietProfile.alcohol_smoking || '');
                $('#tea_coffee_intake').val(state.dietProfile.tea_coffee_intake || '');
                $('#supplements').val(state.dietProfile.supplements || '');
                $('#supplements_text').val(state.dietProfile.supplements_text || '');
            }

            $('#has_known_allergy').trigger('change');
            return true;
        } catch (e) {
            return false;
        }
    }

    function applyServerIntakeToForm(intake) {
        if (!intake) return;
        if (intake.skin_profile) {
            const skin = intake.skin_profile;
            $('#skin_type').val(skin.skin_type || '');
            $('#skin_tone').val(skin.skin_tone || '');
            restoreCheckboxes('skin_concerns[]', skin.skin_concerns);
            restoreCheckboxes('under_eye_issue[]', skin.under_eye_issue);
            restoreCheckboxes('lip_condition[]', skin.lip_condition);
            $('#sensitivity_level').val(skin.sensitivity_level || '');
            $('#additional_concern').val(skin.additional_concern || '');
        }
        if (intake.lifestyle_profile) {
            const lifestyle = intake.lifestyle_profile;
            $('#sleep_hours').val(lifestyle.sleep_hours || '');
            $('#stress_level').val(lifestyle.stress_level || '');
            $('#alcohol_smoking').val(lifestyle.alcohol_smoking || '');
            restoreCheckboxes('medical_conditions[]', lifestyle.medical_conditions);
            $('#medical_conditions_other').val(lifestyle.medical_conditions_other || '');
        }
        if (intake.allergy_profile) {
            const allergy = intake.allergy_profile;
            $('#has_known_allergy').val(allergy.has_known_allergy || '');
            restoreCheckboxes('allergy_type[]', allergy.allergy_type);
            $('#allergy_type_other').val(allergy.allergy_type_other || '');
            $('#reaction_symptoms').val(allergy.reaction_symptoms || '');
            $('#reaction_severity').val(allergy.reaction_severity || '');
            $('#visited_dermatologist').val(allergy.visited_dermatologist || '');
            $('#taking_medication').val(allergy.taking_medication || '');
            $('#additional_allergy_info').val(allergy.additional_allergy_info || '');
            $('#skin_medication').val(allergy.skin_medication || '');
            $('#recent_treatment').val(allergy.recent_treatment || '');
            $('#recent_treatment_other').val(allergy.recent_treatment_other || '');
        }
        if (intake.diet_profile) {
            const diet = intake.diet_profile;
            $('#water_intake').val(diet.water_intake_liters ?? diet.water_intake ?? '');
            $('#fruits_veggies_intake').val(diet.fruits_veggies_intake || '');
            $('#fast_food_freq').val(diet.fast_food_freq || '');
            $('#sugar_consumption').val(diet.sugar_consumption || '');
            $('#alcohol_smoking').val(diet.alcohol_smoking || '');
            $('#tea_coffee_intake').val(diet.tea_coffee_intake || '');
            $('#supplements').val(diet.supplements || '');
            $('#supplements_text').val(diet.supplements_text || '');
        }
        $('#has_known_allergy').trigger('change');
    }

    function loadSavedIntakeFromServer(onDone) {
        if (!localStorage.getItem('access_token')) {
            if (typeof onDone === 'function') onDone(false);
            return;
        }
        $.ajax({
            url: `${API_URL}/profile/intake`,
            type: 'GET',
            headers: getAuthHeaders(),
            success: function(res) {
                applyServerIntakeToForm(res);
                persistWizardState();
                if (typeof onDone === 'function') onDone(true);
            },
            error: function() {
                if (typeof onDone === 'function') onDone(false);
            }
        });
    }

    $('#logout-btn').click(function() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('skinsync_username');
        sessionStorage.removeItem(WIZARD_STATE_KEY);
        localStorage.removeItem(WIZARD_STATE_BACKUP_KEY);
        window.location.reload();
    });

    // ----- Auth Logic -----

    $('#register-form').submit(function(e) {
        e.preventDefault();
        const $btn = $(this).find('button[type="submit"]');
        const data = {
            username: $('#reg-username').val(),
            email: $('#reg-email').val(),
            gender: $('#reg-gender').val(),
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
                if (res.username) {
                    localStorage.setItem('skinsync_username', res.username);
                }
                persistWizardState();
                window.history.replaceState({}, '', '/');
                enterWizard();
                loadSavedIntakeFromServer(function() {
                    showStep(currentStep);
                });
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
        const completedSteps = Math.max(step - 1, 0);
        const percent = Math.round((completedSteps / totalSteps) * 100);
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
            persistWizardState();
            showStep(currentStep);
        }
    });

    $(document).on('input change', 'input, select, textarea', function() {
        persistWizardState();
    });

    function submitStep(formSelector, url, buildData, nextStep) {
        $(formSelector).submit(function(e) {
            e.preventDefault();
            const $btn = $(this).find('button[type="submit"]');
            const formEl = this;
            if (!formEl.checkValidity()) {
                formEl.reportValidity();
                return;
            }
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
            $('#allergy_details_section [required]').prop('required', true);
        } else {
            $('#allergy_details_section').addClass('d-none').removeClass('fade-in');
            $('#allergy_details_section [required]').prop('required', false);
        }
    });

    submitStep('#form-step-3', '/profile/allergy', function() {
        function checkboxValues(name) { return $(`input[name="${name}"]:checked`).map(function(){ return this.value; }).get(); }
        return {
            has_known_allergy: $('#has_known_allergy').val(),
            allergy_type: checkboxValues('allergy_type[]'),
            allergy_type_other: $('#allergy_type_other').val(),
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
    const $cameraViewfinder = $('.camera-viewfinder');
    const cameraVideo = document.getElementById('camera-video');
    const cameraCanvas = document.getElementById('camera-canvas');
    const cameraGuide = document.querySelector('.camera-face-guide');
    const cameraGuideBadge = document.getElementById('camera-guide-badge');
    const cameraGuideText = document.getElementById('camera-guide-text');
    const cameraFlash = document.getElementById('camera-capture-flash');
    let cameraStream = null;
    let cameraAutoTimer = null;
    let cameraTrackingActive = false;
    let cameraTrackingInProgress = false;
    let faceStableHits = 0;
    let faceMesh = null;
    let faceMeshLastResult = null;
    let captureCountdownTimer = null;
    let captureCountdownRunning = false;

    function ensureFaceMesh() {
        if (faceMesh || typeof FaceMesh === 'undefined') return faceMesh;
        faceMesh = new FaceMesh({
            locateFile: function(file) {
                return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
            }
        });
        faceMesh.setOptions({
            maxNumFaces: 1,
            refineLandmarks: true,
            minDetectionConfidence: 0.55,
            minTrackingConfidence: 0.55
        });
        faceMesh.onResults(function(results) {
            faceMeshLastResult = results;
        });
        return faceMesh;
    }

    function clearCameraAutoTracking() {
        cameraTrackingActive = false;
        cameraTrackingInProgress = false;
        faceStableHits = 0;
        if (cameraAutoTimer) {
            cancelAnimationFrame(cameraAutoTimer);
            cameraAutoTimer = null;
        }
        if (captureCountdownTimer) {
            clearTimeout(captureCountdownTimer);
            captureCountdownTimer = null;
        }
        captureCountdownRunning = false;
        if (cameraGuideBadge) {
            cameraGuideBadge.classList.remove('is-left', 'is-right', 'is-center', 'is-too-close', 'is-off', 'is-pulse');
        }
    }

    function faceInsideGuide(bounds) {
        if (!bounds || !cameraVideo || !cameraGuide) return false;
        const videoRect = cameraVideo.getBoundingClientRect();
        const guideRect = cameraGuide.getBoundingClientRect();
        const faceLeft = videoRect.left + bounds.x;
        const faceTop = videoRect.top + bounds.y;
        const faceRight = faceLeft + bounds.width;
        const faceBottom = faceTop + bounds.height;
        const overlapX = Math.min(faceRight, guideRect.right) - Math.max(faceLeft, guideRect.left);
        const overlapY = Math.min(faceBottom, guideRect.bottom) - Math.max(faceTop, guideRect.top);
        const overlapArea = Math.max(0, overlapX) * Math.max(0, overlapY);
        const faceArea = Math.max(1, bounds.width * bounds.height);
        const coverage = overlapArea / faceArea;
        const centeredX = Math.abs((faceLeft + faceRight) / 2 - guideRect.left - guideRect.width / 2) / guideRect.width;
        const centeredY = Math.abs((faceTop + faceBottom) / 2 - guideRect.top - guideRect.height / 2) / guideRect.height;
        return coverage >= 0.72 && centeredX <= 0.18 && centeredY <= 0.18;
    }

    function setCameraGuideState(state, text) {
        if (cameraGuideBadge) {
            cameraGuideBadge.classList.remove('is-left', 'is-right', 'is-center', 'is-too-close', 'is-off', 'is-pulse');
            cameraGuideBadge.classList.add(`is-${state}`);
            cameraGuideBadge.classList.add('is-pulse');
            window.setTimeout(function() {
                cameraGuideBadge.classList.remove('is-pulse');
            }, 240);
        }
        if (cameraGuideText) {
            cameraGuideText.textContent = text;
        }
    }

    function runCaptureCountdown(done) {
        if (captureCountdownRunning) return;
        captureCountdownRunning = true;
        const steps = [
            { label: '3', hint: 'Capturing in 3...' },
            { label: '2', hint: 'Capturing in 2...' },
            { label: '1', hint: 'Capturing in 1...' },
            { label: 'Click!', hint: 'Click!' }
        ];

        let index = 0;
        const stepNext = function() {
            if (!cameraTrackingActive) {
                captureCountdownRunning = false;
                return;
            }
            const step = steps[index];
            if (cameraGuideText) cameraGuideText.textContent = step.label;
            $('#camera-angle-hint').text(step.hint);
            if (cameraGuideBadge) cameraGuideBadge.classList.add('is-pulse');
            window.setTimeout(function() {
                if (cameraGuideBadge) cameraGuideBadge.classList.remove('is-pulse');
            }, 180);
            index += 1;
            if (index < steps.length) {
                captureCountdownTimer = window.setTimeout(stepNext, 250);
            } else {
                captureCountdownRunning = false;
                done();
            }
        };

        stepNext();
    }

    function faceBoxFromLandmarks(landmarks) {
        if (!landmarks || !landmarks.length || !cameraVideo) return null;
        let minX = 1;
        let minY = 1;
        let maxX = 0;
        let maxY = 0;
        landmarks.forEach(function(point) {
            minX = Math.min(minX, point.x);
            minY = Math.min(minY, point.y);
            maxX = Math.max(maxX, point.x);
            maxY = Math.max(maxY, point.y);
        });
        return {
            x: minX * cameraVideo.videoWidth,
            y: minY * cameraVideo.videoHeight,
            width: (maxX - minX) * cameraVideo.videoWidth,
            height: (maxY - minY) * cameraVideo.videoHeight
        };
    }

    function captureCurrentFrame() {
        if (!cameraStream || !cameraVideo.videoWidth) {
            showToast('The camera is still starting. Please try again.', 'info');
            return;
        }
        if ($cameraViewfinder.length) {
            $cameraViewfinder.addClass('is-capturing');
            window.setTimeout(function() {
                $cameraViewfinder.removeClass('is-capturing');
            }, 280);
        }
        if (cameraFlash) {
            cameraFlash.style.opacity = '1';
            window.setTimeout(function() {
                cameraFlash.style.opacity = '0';
            }, 260);
        }
        const targetWidth = Math.min(cameraVideo.videoWidth, 960);
        const scale = targetWidth / cameraVideo.videoWidth;
        const targetHeight = Math.round(cameraVideo.videoHeight * scale);
        cameraCanvas.width = targetWidth;
        cameraCanvas.height = targetHeight;
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
            const captureLabel = selectedFiles.length >= 3
                ? 'Photo captured. Minimum complete — you can submit now.'
                : `Photo captured. Next: capture the ${nextView}.`;
            $('#camera-angle-hint').text(captureLabel);
            setCameraGuideState(selectedFiles.length >= 3 ? 'center' : (selectedFiles.length === 1 ? 'left' : 'right'),
                selectedFiles.length >= 3 ? 'Captured' : `Next ${nextView}`);
            showToast('Photo captured successfully.', 'success');
        }, 'image/jpeg', 0.82);
    }

    function startCameraAutoTracking() {
        clearCameraAutoTracking();
        if (!cameraStream || !cameraVideo.videoWidth) return;
        if (typeof FaceMesh === 'undefined') {
            $('#camera-angle-hint').text('Live guidance is not supported in this browser. Use the Capture Photo button.');
            setCameraGuideState('off', 'Use capture button');
            return;
        }
        ensureFaceMesh();
        if (!faceMesh) {
            $('#camera-angle-hint').text('Live guidance is not ready yet. Use the Capture Photo button.');
            setCameraGuideState('off', 'Use capture button');
            return;
        }
        cameraTrackingActive = true;
        $('#camera-angle-hint').text('Hold still — we will capture automatically when your face is centered.');
        setCameraGuideState('off', 'Center your face');

        const tick = async function() {
            if (!cameraTrackingActive || !cameraStream) return;
            if (cameraTrackingInProgress || !cameraVideo.videoWidth) {
                cameraAutoTimer = requestAnimationFrame(tick);
                return;
            }
            cameraTrackingInProgress = true;
            try {
                await faceMesh.send({ image: cameraVideo });
                const landmarks = faceMeshLastResult?.multiFaceLandmarks?.[0];
                const faceBox = faceBoxFromLandmarks(landmarks);
                if (faceBox && faceInsideGuide(faceBox)) {
                    faceStableHits += 1;
                    if (!captureCountdownRunning) {
                        setCameraGuideState('center', 'Face centered');
                        runCaptureCountdown(function() {
                            cameraTrackingActive = false;
                            captureCurrentFrame();
                        });
                        return;
                    }
                } else {
                    faceStableHits = 0;
                    if (captureCountdownTimer) {
                        clearTimeout(captureCountdownTimer);
                        captureCountdownTimer = null;
                    }
                    captureCountdownRunning = false;
                    if (faceBox) {
                        const faceCenterX = faceBox.x + (faceBox.width / 2);
                        const faceCenterY = faceBox.y + (faceBox.height / 2);
                        const frameCenterX = cameraVideo.videoWidth / 2;
                        const frameCenterY = cameraVideo.videoHeight / 2;
                        const horizontalOffset = faceCenterX - frameCenterX;
                        const verticalOffset = faceCenterY - frameCenterY;
                        const faceScale = Math.max(faceBox.width, faceBox.height);
                        const closeThreshold = Math.min(cameraVideo.videoWidth, cameraVideo.videoHeight) * 0.22;
                        const moveThresholdX = Math.max(80, cameraVideo.videoWidth * 0.08);
                        const moveThresholdY = Math.max(60, cameraVideo.videoHeight * 0.07);

                        if (faceScale < closeThreshold) {
                            $('#camera-angle-hint').text('Move closer to the camera.');
                            setCameraGuideState('too-close', 'Come closer');
                        } else if (Math.abs(horizontalOffset) > moveThresholdX) {
                            if (horizontalOffset > 0) {
                                $('#camera-angle-hint').text('Move a little left so your face sits in the circle.');
                                setCameraGuideState('left', 'Move left');
                            } else {
                                $('#camera-angle-hint').text('Move a little right so your face sits in the circle.');
                                setCameraGuideState('right', 'Move right');
                            }
                        } else if (Math.abs(verticalOffset) > moveThresholdY) {
                            if (verticalOffset > 0) {
                                $('#camera-angle-hint').text('Raise your face slightly to center it.');
                                setCameraGuideState('center', 'Move up');
                            } else {
                                $('#camera-angle-hint').text('Lower your face slightly to center it.');
                                setCameraGuideState('center', 'Move down');
                            }
                        } else {
                            $('#camera-angle-hint').text('Hold still — face is nearly centered.');
                            setCameraGuideState('center', 'Hold still');
                        }
                    } else {
                        $('#camera-angle-hint').text('Move into the circle so we can detect your face.');
                        setCameraGuideState('off', 'Face not found');
                    }
                }
            } catch (error) {
                faceStableHits = 0;
            } finally {
                cameraTrackingInProgress = false;
            }
            cameraAutoTimer = requestAnimationFrame(tick);
        };

        cameraAutoTimer = requestAnimationFrame(tick);
    }

    function stopCamera() {
        clearCameraAutoTracking();
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
            cameraVideo.onloadedmetadata = function() {
                cameraVideo.play().catch(function() {});
                setCameraGuideState('off', 'Center your face');
                startCameraAutoTracking();
            };
        } catch (error) {
            showToast(error.name === 'NotAllowedError'
                ? 'Camera permission was denied. Please allow camera access and try again.'
                : 'Could not open the camera. You can still select images from your device.', 'error');
            stopCamera();
        }
    });

    $('#close-camera-btn').on('click', stopCamera);

    $('#capture-photo-btn').on('click', function() {
        captureCurrentFrame();
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
            $('#file-count').text(`${selectedFiles.length} image(s) selected â€” add at least ${3 - selectedFiles.length} more.`);
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
                const reportStatus = res.status || res.report?.status;
                if (reportStatus !== 'ok') {
                    const retryMessage = res.msg || res.report?.message || 'Image analysis failed. Please upload new images or click new images and submit again.';
                    $('.step-content').addClass('d-none').removeClass('active');
                    $('#step-success').removeClass('d-none').addClass('active fade-in');
                    $('#form-progress').css('width', `100%`);
                    $('#progress-percent').text(100);
                    $('.step-list-item').removeClass('active').addClass('completed');
                    $('#header-status').text('Assessment Incomplete');
                    $('#report-container').html(`
                        <div class="report-launch-card report-launch-card-error">
                            <div class="report-launch-message">
                                <span class="report-launch-kicker">Image Analysis Issue</span>
                                <h3>We could not extract usable facial images</h3>
                                <p>${retryMessage}</p>
                                <div class="report-launch-meta">
                                    <span class="report-launch-pill">Upload new images</span>
                                    <span class="report-launch-pill">Or capture new images</span>
                                </div>
                            </div>
                            <div class="report-launch-action">
                                <button type="button" class="btn-success btn-ai-action btn-ai-action-lg" id="retry-images-btn">
                                    <span>Try Again</span>
                                </button>
                            </div>
                        </div>
                    `);
                    selectedFiles = [];
                    syncFileInput();
                    renderPreviews();
                    persistWizardState();
                    showToast(retryMessage, 'error');
                    return;
                }
                $('.step-content').addClass('d-none').removeClass('active');
                $('#step-success').removeClass('d-none').addClass('active fade-in');
                $('#form-progress').css('width', `100%`);
                $('#progress-percent').text(100);
                $('.step-list-item').removeClass('active').addClass('completed');
                $('#header-status').text('Assessment Complete');
                if (res.report) {
                    sessionStorage.setItem('skinsync_last_report_id', res.report.id);
                    const clinicalReportHtml = res.report.id
                        ? `<div class="report-launch-action">
                                <button type="button" class="btn-success btn-ai-action btn-ai-action-lg" id="clinical-report-btn" data-report-id="${res.report.id}">
                                    <span>Clinical Report</span>
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h12M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                </button>
                           </div>`
                        : '';
                    $('#report-container').html(`
                        <div class="report-launch-card">
                            <div class="report-launch-message">
                                <span class="report-launch-kicker">Assessment Complete</span>
                                <h3>Assessment Complete</h3>
                                <p>Your clinical profile has been securely recorded and the AI diagnostics engine has analyzed your uploaded imaging.</p>
                                <div class="report-launch-meta">
                                    <span class="report-launch-pill">Saved to history</span>
                                    <span class="report-launch-pill">Ready for clinical report</span>
                                </div>
                            </div>
                            ${clinicalReportHtml}
                        </div>
                    `);
                }
                // Do not retain one assessment's photos for a later submission/user.
                selectedFiles = [];
                syncFileInput();
                renderPreviews();
                persistWizardState();
            },
            error: function(err) {
                showToast(err.responseJSON?.msg || 'Error uploading images', 'error');
            },
            complete: function() { setButtonLoading($btn, false); }
        });
    });

    $(document).on('click', '#retry-images-btn', function() {
        $('.step-content').addClass('d-none').removeClass('active');
        $('#step-5').removeClass('d-none').addClass('active fade-in');
        $('#header-status').text('Clinical Assessment In Progress');
    });

    $(document).on('click', '#clinical-report-btn', function() {
        const reportId = $(this).data('report-id');
        sessionStorage.setItem('skinsync_report_return_url', window.location.href);
        window.location.href = `/reports/${reportId}`;
    });

    // ----- History -----

    function buildHistoryListItemHtml(r) {
        if (r.status !== 'ok') {
            return `
                <a href="/reports/${r.id}" class="history-list-item history-report-link" data-report-id="${r.id}">
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
            <a href="/reports/${r.id}" class="history-list-item history-report-link" data-report-id="${r.id}">
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

    $(document).on('click', '.history-report-link', function(e) {
        e.preventDefault();
        sessionStorage.setItem(RETURN_TO_WIZARD_KEY, '1');
        sessionStorage.setItem('skinsync_report_return_url', '/');
        window.location.href = $(this).attr('href');
    });

    $('#history-btn').on('click', function() {
        loadHistoryList();
        const modalEl = document.getElementById('history-modal');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    });

});







