/**
 * Initializes the form wizard for a multi-step form with navigation, validation, and dynamic tables.
 */
function initializeFormWizard(form) {
    console.log("Initializing form wizard for form:", form);

    // Select elements
    const tabs = form.querySelectorAll('button[data-bs-toggle="pill"]');
    const tabPanes = form.querySelectorAll('.tab-pane');
    const totalSteps = tabs.length;
    const saveButton = form.querySelector('#salvar-entrevista');

    // Validation state for each tab
    const tabValidationState = {};

    if (!tabs.length || !tabPanes.length) {
        console.error("No tabs or tab panes found", { tabs: tabs.length, tabPanes: tabPanes.length });
        return;
    }

    if (!saveButton) {
        console.error("Save button with ID 'salvar-entrevista' not found");
    }

    // Store original icons for each tab
    tabs.forEach(tab => {
        const icon = tab.querySelector(".step-icon");
        if (icon) {
            tab.setAttribute("data-original-icon", icon.className);
            console.log("Stored original icon for tab:", { tab: tab.id, icon: icon.className });
        }
    });

    /**
     * Updates the progress bar based on the current step.
     * @param {number} stepIndex - The index of the current step (0-based).
     */
    function updateProgressBar(stepIndex) {
        const progressBars = document.querySelectorAll("[id^=progress-bar-]");
        if (progressBars.length === 0) {
            console.error("No progress bars found.");
            return;
        }
        if (progressBars.length !== totalSteps) {
            console.warn("Number of progress bars does not match total steps", {
                found: progressBars.length,
                expected: totalSteps
            });
        }

        progressBars.forEach((bar, index) => {
            bar.classList.remove("active");
            bar.style.width = "14.29%"; // 100% / 7 steps
            if (index <= stepIndex) {
                bar.classList.remove("hidden");
                if (index === stepIndex) {
                    bar.classList.add("active");
                }
            } else {
                bar.classList.add("hidden");
            }
            console.log("Updated progress bar:", {
                id: bar.id,
                active: bar.classList.contains("active"),
                hidden: bar.classList.contains("hidden"),
                step: index + 1
            });
        });
    }

    /**
     * Updates the save button state based on form validity.
     */
    function updateSaveButtonState() {
        if (!saveButton) return;
        let isValid = true;
        const requiredInputs = form.querySelectorAll(".form-control:not([readonly])[required]");
        requiredInputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
            }
        });
        saveButton.disabled = !isValid;
        console.log("Save button state updated. Valid:", isValid, "Required inputs:", requiredInputs.length);
    }

    /**
     * Validates inputs with a pattern attribute.
     * @param {HTMLInputElement} input - The input element to validate.
     * @returns {string|null} Error message if invalid, null if valid.
     */
    function validatePatternInput(input) {
        const pattern = input.getAttribute("pattern");
        const label = input.getAttribute("data-label") || input.name;
        if (pattern && input.value && !input.value.match(new RegExp(pattern))) {
            return `O campo ${label} não corresponde ao formato esperado.`;
        }
        return null;
    }

    /**
     * Validates required fields in a specific tab.
     * @param {HTMLElement} tabPane - The tab pane to validate.
     * @returns {Array<string>} List of error messages.
     */
    function getTabErrors(tabPane) {
        const requiredInputs = tabPane.querySelectorAll(".form-control:not([readonly])[required], .form-select[required]");
        const errors = [];

        requiredInputs.forEach(input => {
            const label = input.getAttribute("data-label") || input.name;
            if (!input.value.trim()) {
                errors.push(`O campo ${label} é obrigatório.`);
                input.classList.add("is-invalid");
            } else {
                input.classList.remove("is-invalid");
            }

            const patternError = validatePatternInput(input);
            if (patternError) {
                errors.push(patternError);
                input.classList.add("is-invalid");
            }
        });

        console.log("Tab errors checked:", { tab: tabPane.id, errors });
        return errors;
    }

    /**
     * Validates the current tab and displays errors.
     * @param {HTMLElement} currentTab - The active tab pane.
     * @returns {boolean} True if valid, false if invalid.
     */
    function validateCurrentTab(currentTab) {
        const errorContainer = currentTab.querySelector(".validation-errors");
        const errors = getTabErrors(currentTab);

        tabValidationState[currentTab.id] = {
            valid: errors.length === 0,
            errors
        };

        if (errorContainer) {
            if (errors.length > 0) {
                errorContainer.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <ul class="mb-0">
                            ${errors.map(error => `<li>${error}</li>`).join('')}
                        </ul>
                    </div>
                `;
            } else {
                errorContainer.innerHTML = '';
            }
        }

        console.log("Tab validation:", { tab: currentTab.id, valid: errors.length === 0, errors });
        return errors.length === 0;
    }

    /**
     * Updates the validation status of all tabs and signals invalid ones.
     */
    function updateTabSignals() {
        const currentTab = form.querySelector(".tab-pane.show");
        if (currentTab) {
            validateCurrentTab(currentTab);
        }

        tabs.forEach(tab => {
            const tabPaneId = tab.getAttribute("data-bs-target").substring(1);
            const navTab = tab;

            navTab.classList.remove("invalid");
            const existingIcon = navTab.querySelector(".error-icon");
            if (existingIcon) {
                existingIcon.remove();
            }
            const icon = navTab.querySelector(".step-icon");
            if (icon && navTab.hasAttribute("data-original-icon")) {
                icon.className = navTab.getAttribute("data-original-icon");
            }

            if (tabValidationState[tabPaneId] && !tabValidationState[tabPaneId].valid) {
                navTab.classList.add("invalid");
                if (icon) {
                    icon.className = "ri-close-circle-fill text-danger me-2 step-icon";
                }
                const errorIcon = document.createElement("i");
                errorIcon.className = "ri-error-warning-fill text-danger ms-2 error-icon";
                navTab.appendChild(errorIcon);
                console.log("Applied invalid to tab:", {
                    tab: navTab.id,
                    errors: tabValidationState[tabPaneId].errors
                });
            }
        });
    }

    // Initialize tab navigation and progress
    tabs.forEach((tab, index) => {
        tab.setAttribute("data-position", index);
        tab.addEventListener("click", () => {
            const currentTab = form.querySelector(".tab-pane.show");
            if (currentTab) {
                form.classList.add("was-validated");
                validateCurrentTab(currentTab);
            }

            console.log("Tab clicked:", tab.id);
            form.classList.remove("was-validated");
            updateProgressBar(index);
            tabs.forEach((t, i) => {
                t.classList.toggle("done", i <= index && !t.classList.contains("active"));
            });
            tabs.forEach(t => t.removeAttribute("aria-current"));
            tab.setAttribute("aria-current", "step");
            updateTabSignals();
        });
    });

    // Handle nexttab buttons
    form.querySelectorAll(".nexttab").forEach(button => {
        button.addEventListener("click", () => {
            const currentTab = form.querySelector(".tab-pane.show");
            if (!currentTab) {
                console.error("No active tab found");
                return;
            }

            form.classList.add("was-validated");
            if (validateCurrentTab(currentTab)) {
                const nextTabId = button.getAttribute("data-nexttab");
                const nextTab = document.getElementById(nextTabId);
                if (nextTab) {
                    console.log("Navigating to next tab:", nextTabId);
                    nextTab.click();
                    form.classList.remove("was-validated");
                } else {
                    console.error(`Next tab with ID ${nextTabId} not found`);
                }
            }
            updateTabSignals();
        });
    });

    // Handle previestab buttons
    form.querySelectorAll(".previestab").forEach(button => {
        button.addEventListener("click", () => {
            const prevTabId = button.getAttribute("data-previous");
            const doneTabs = form.querySelectorAll(".custom-nav .done");
            if (doneTabs.length > 0) {
                doneTabs[doneTabs.length - 1].classList.remove("done");
            }
            const prevTab = document.getElementById(prevTabId);
            if (prevTab) {
                console.log("Navigating to previous tab:", prevTabId);
                prevTab.click();
                form.classList.remove("was-validated");
                const currentTab = form.querySelector(".tab-pane.show");
                if (currentTab) {
                    currentTab.querySelector(".validation-errors").innerHTML = '';
                }
            } else {
                console.error(`Previous tab with ID ${prevTabId} not found`);
            }
            updateTabSignals();
        });
    });

    // Validate inputs and update save button state
    form.querySelectorAll(".form-control:not([readonly])[required], .form-select[required]").forEach(input => {
        input.addEventListener("input", () => {
            updateSaveButtonState();
            validatePatternInput(input);
            const currentTab = form.querySelector(".tab-pane.show");
            if (currentTab && input.closest(".tab-pane") === currentTab) {
                validateCurrentTab(currentTab);
            }
            updateTabSignals();
        });
    });

    // Handle pattern validation
    form.querySelectorAll(".form-control[pattern]").forEach(input => {
        input.addEventListener("input", () => {
            validatePatternInput(input);
            updateTabSignals();
        });
    });

    // Handle form submission
    if (saveButton) {
        saveButton.addEventListener("click", (event) => {
            event.preventDefault();
            form.classList.add("was-validated");
            let isValid = true;

            form.querySelectorAll(".form-control:not([readonly])[required], .form-select[required]").forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add("is-invalid");
                    input.reportValidity();
                } else {
                    input.classList.remove("is-invalid");
                }
            });

            if (isValid) {
                console.log("Submitting form via AJAX to:", form.action);
                fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form),
                    headers: {
                        'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
                        'Accept': 'application/json'
                    }
                }).then(response => {
                    console.log("Response status:", response.status, "URL:", form.action);
                    if (!response.ok) {
                        return response.text().then(text => {
                            console.error("Response text:", text);
                            throw new Error(`HTTP error! Status: ${response.status}, Response: ${text}`);
                        });
                    }
                    return response.json();
                }).then(data => {
                    console.log("Form submitted successfully:", data);
                    new bootstrap.Toast(document.getElementById('successToast')).show();
                    setTimeout(() => {
                        window.location.href = "{% url 'entrevistas:lista' %}";
                    }, 2000);
                }).catch(error => {
                    console.error("Submission error:", error.message);
                    const errorToast = document.getElementById('errorToast');
                    errorToast.querySelector('.toast-body').textContent = error.message;
                    new bootstrap.Toast(errorToast).show();
                });
            } else {
                console.log("Form validation failed");
                const currentTab = form.querySelector(".tab-pane.show");
                if (currentTab) {
                    validateCurrentTab(currentTab);
                }
                updateTabSignals();
            }
        });
    }

    // Handle dynamic caregiver table
    const caregiverButton = document.getElementById('inserirCuidadorBtn');
    if (caregiverButton) {
        caregiverButton.addEventListener('click', () => {
            const tbody = document.getElementById('cuidadorTableBody');
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="text" name="cuidador_nome[]" class="form-control" required data-label="Nome do Cuidador"></td>
                <td><input type="text" name="cuidador_parentesco[]" class="form-control"></td>
                <td><input type="text" name="cuidador_telefone[]" class="form-control" pattern="^\\d{10,11}$" title="Digite um telefone válido (10 ou 11 dígitos)" data-label="Telefone do Cuidador"></td>
                <td><input type="checkbox" name="cuidador_is_cuidador[]"></td>
                <td><input type="checkbox" name="cuidador_is_responsavel[]"></td>
                <td><button type="button" class="btn btn-danger btn-sm remove-cuidador">Remover</button></td>
            `;
            tbody.appendChild(row);

            row.querySelector('.remove-cuidador').addEventListener('click', () => {
                row.remove();
                updateSaveButtonState();
                const currentTab = form.querySelector(".tab-pane.show");
                if (currentTab) {
                    validateCurrentTab(currentTab);
                }
                updateTabSignals();
            });

            updateSaveButtonState();
            row.querySelectorAll(".form-control[pattern]").forEach(input => {
                input.addEventListener("input", () => {
                    validatePatternInput(input);
                    const currentTab = form.querySelector(".tab-pane.show");
                    if (currentTab) {
                        validateCurrentTab(currentTab);
                    }
                    updateTabSignals();
                });
            });

            row.querySelectorAll(".form-control:not([readonly])[required]").forEach(input => {
                input.addEventListener("input", () => {
                    updateSaveButtonState();
                    validateCurrentTab(form.querySelector(".tab-pane.show"));
                    updateTabSignals();
                });
            });

            updateTabSignals();
        });
    }

    // Handle dynamic doador table
    const doadorButton = document.getElementById('inserirDoadorBtn');
    if (doadorButton) {
        doadorButton.addEventListener('click', () => {
            const tbody = document.getElementById('doadorTableBody');
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="text" name="doador_nome[]" class="form-control" required data-label="Nome"></td>
                <td><input type="text" name="doador_cpf[]" class="form-control" pattern="\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}" required title="Formato: XXX.XXX.XXX-XX" data-label="CPF"></td>
                <td><input type="text" name="doador_rg[]" class="form-control" data-label="RG"></td>
                <td>
                    <select name="doador_estado_civil[]" class="form-select" required data-label="Estado Civil">
                        <option value="">Selecione</option>
                        <option value="solteiro">Solteiro</option>
                        <option value="casado">Casado</option>
                        <option value="divorciado">Divorciado</option>
                        <option value="viúvo">Viúvo</option>
                    </select>
                </td>
                <td>
                    <select name="doador_sexo[]" class="form-select" required data-label="Sexo">
                        <option value="">Selecione</option>
                        <option value="masculino">Masculino</option>
                        <option value="feminino">Feminino</option>
                        <option value="outro">Outro</option>
                    </select>
                </td>
                <td><input type="text" name="doador_pai[]" class="form-control" data-label="Nome do Pai"></td>
                <td><input type="text" name="doador_mae[]" class="form-control" data-label="Nome da Mãe"></td>
                <td><input type="text" name="doador_escolaridade[]" class="form-control" data-label="Escolaridade"></td>
                <td><input type="text" name="doador_profissao[]" class="form-control" data-label="Profissão"></td>
                <td><input type="text" name="doador_endereco[]" class="form-control" required data-label="Endereço"></td>
                <td><input type="text" name="doador_telefone[]" class="form-control" pattern="\\d{10,11}" title="10 ou 11 dígitos" data-label="Telefone"></td>
                <td><input type="email" name="doador_email[]" class="form-control" data-label="Email"></td>
                <td><input type="date" name="doador_data_nascimento[]" class="form-control" required data-label="Data de Nascimento"></td>
                <td><button type="button" class="btn btn-danger btn-sm remove-doador">Remover</button></td>
            `;
            tbody.appendChild(row);

            row.querySelector('.remove-doador').addEventListener('click', () => {
                row.remove();
                updateSaveButtonState();
                const currentTab = form.querySelector(".tab-pane.show");
                if (currentTab) {
                    validateCurrentTab(currentTab);
                }
                updateTabSignals();
            });

            updateSaveButtonState();
            row.querySelectorAll(".form-control[pattern]").forEach(input => {
                input.addEventListener("input", () => {
                    validatePatternInput(input);
                    const currentTab = form.querySelector(".tab-pane.show");
                    if (currentTab) {
                        validateCurrentTab(currentTab);
                    }
                    updateTabSignals();
                });
            });

            row.querySelectorAll(".form-control:not([readonly])[required], .form-select[required]").forEach(input => {
                input.addEventListener("input", () => {
                    updateSaveButtonState();
                    validateCurrentTab(form.querySelector(".tab-pane.show"));
                    updateTabSignals();
                });
            });

            updateTabSignals();
        });
    }

    // Initialize
    updateSaveButtonState();
    updateTabSignals();
    updateProgressBar(0);
}

// Initialize all forms
document.querySelectorAll(".form-steps").forEach(form => {
    console.log("Found form with .form-steps:", form);
    initializeFormWizard(form);
});


document.addEventListener('DOMContentLoaded', function () {
    // Wizard Navigation
    const navLinks = document.querySelectorAll('.nav-link');
    const progressBars = document.querySelectorAll('.progress-bar');
    const nextButtons = document.querySelectorAll('.nexttab');
    const prevButtons = document.querySelectorAll('.previestab');
    const form = document.querySelector('.form-steps');
    const pacienteId = form.getAttribute('data-paciente-id');

    navLinks.forEach((link, index) => {
        link.addEventListener('click', function () {
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            progressBars.forEach((bar, barIndex) => {
                bar.classList.remove('bg-info', 'bg-secondary', 'bg-success', 'bg-warning', 'bg-danger');
                if (barIndex <= index) {
                    bar.classList.add(`bg-${['info', 'secondary', 'success', 'warning', 'danger'][barIndex]}`);
                }
            });
        });
    });

    nextButtons.forEach(button => {
        button.addEventListener('click', function () {
            const nextTabId = this.getAttribute('data-nexttab');
            const nextTab = document.getElementById(nextTabId);
            if (nextTab) {
                nextTab.click();
            }
        });
    });

    prevButtons.forEach(button => {
        button.addEventListener('click', function () {
            const prevTabId = this.getAttribute('data-previous');
            const prevTab = document.getElementById(prevTabId);
            if (prevTab) {
                prevTab.click();
            }
        });
    });

    // Modal Handling for Doador
    const inserirDoadorBtn = document.getElementById('inserirDoadorBtn');
    const doadorModal = new bootstrap.Modal(document.getElementById('doadorModal'), {});
    const doadorForm = document.getElementById('doadorForm');

    inserirDoadorBtn.addEventListener('click', function () {
        doadorForm.reset();
        doadorModal.show();
    });

    doadorForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(doadorForm);
        formData.append('paciente_id', pacienteId);

        fetch('/entrevistas/adicionar_doador/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tbody = document.getElementById('doadorTableBody');
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${data.doador.nome}</td>
                    <td>${data.doador.cpf}</td>
                    <td>${data.doador.rg}</td>
                    <td>${data.doador.estado_civil}</td>
                    <td>${data.doador.sexo}</td>
                    <td>${data.doador.nome_pai}</td>
                    <td>${data.doador.nome_mae}</td>
                    <td>${data.doador.escolaridade}</td>
                    <td>${data.doador.profissao}</td>
                    <td>${data.doador.endereco}</td>
                    <td>${data.doador.telefone}</td>
                    <td>${data.doador.email}</td>
                    <td>${data.doador.data_nascimento}</td>
                    <td><button type="button" class="btn btn-danger btn-sm delete-doador" data-id="${data.doador.id}">Excluir</button></td>
                `;
                tbody.appendChild(row);
                doadorModal.hide();
                showToast('successToast', 'Doador adicionado com sucesso!');
            } else {
                showToast('errorToast', data.error || 'Erro ao adicionar doador.');
            }
        })
        .catch(error => {
            showToast('errorToast', 'Erro ao adicionar doador.');
            console.error('Error:', error);
        });
    });

    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('delete-doador')) {
            const doadorId = e.target.getAttribute('data-id');
            if (confirm('Tem certeza que deseja excluir este doador?')) {
                fetch(`/entrevistas/remover_doador/${doadorId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        e.target.closest('tr').remove();
                        showToast('successToast', 'Doador removido com sucesso!');
                    } else {
                        showToast('errorToast', data.error || 'Erro ao remover doador.');
                    }
                })
                .catch(error => {
                    showToast('errorToast', 'Erro ao remover doador.');
                    console.error('Error:', error);
                });
            }
        }
    });

    // Modal Handling for Cuidador
    const inserirCuidadorBtn = document.getElementById('inserirCuidadorBtn');
    const cuidadorModal = new bootstrap.Modal(document.getElementById('cuidadorModal'), {});
    const cuidadorForm = document.getElementById('cuidadorForm');

    inserirCuidadorBtn.addEventListener('click', function () {
        cuidadorForm.reset();
        cuidadorModal.show();
    });

    cuidadorForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(cuidadorForm);
        formData.append('paciente_id', pacienteId);

        fetch('/entrevistas/adicionar_cuidador/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tbody = document.getElementById('cuidadorTableBody');
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${data.cuidador.nome}</td>
                    <td>${data.cuidador.grau_parentesco}</td>
                    <td>${data.cuidador.telefone}</td>
                    <td>${data.cuidador.is_cuidador ? 'Sim' : 'Não'}</td>
                    <td>${data.cuidador.is_responsavel ? 'Sim' : 'Não'}</td>
                    <td><button type="button" class="btn btn-danger btn-sm delete-cuidador" data-id="${data.cuidador.id}">Excluir</button></td>
                `;
                tbody.appendChild(row);
                cuidadorModal.hide();
                showToast('successToast', 'Cuidador adicionado com sucesso!');
            } else {
                showToast('errorToast', data.error || 'Erro ao adicionar cuidador.');
            }
        })
        .catch(error => {
            showToast('errorToast', 'Erro ao adicionar cuidador.');
            console.error('Error:', error);
        });
    });

    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('delete-cuidador')) {
            const cuidadorId = e.target.getAttribute('data-id');
            if (confirm('Tem certeza que deseja excluir este cuidador?')) {
                fetch(`/entrevistas/remover_cuidador/${cuidadorId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        e.target.closest('tr').remove();
                        showToast('successToast', 'Cuidador removido com sucesso!');
                    } else {
                        showToast('errorToast', data.error || 'Erro ao remover cuidador.');
                    }
                })
                .catch(error => {
                    showToast('errorToast', 'Erro ao remover cuidador.');
                    console.error('Error:', error);
                });
            }
        }
    });


    document.addEventListener('DOMContentLoaded', function () {
    // Wizard Navigation
    const navLinks = document.querySelectorAll('.nav-link');
    const progressBars = document.querySelectorAll('.progress-bar');
    const nextButtons = document.querySelectorAll('.nexttab');
    const prevButtons = document.querySelectorAll('.previestab');
    const form = document.querySelector('.form-steps');
    const pacienteId = form ? form.getAttribute('data-paciente-id') : null;
    const saveButton = document.getElementById('salvar-entrevista');

    if (!form || !pacienteId) {
        console.error('Form or paciente_id not found');
        return;
    }

    navLinks.forEach((link, index) => {
        link.addEventListener('click', function () {
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            progressBars.forEach((bar, barIndex) => {
                bar.classList.remove('bg-info', 'bg-secondary', 'bg-success', 'bg-warning', 'bg-dark', 'bg-danger');
                if (barIndex <= index) {
                    bar.classList.add(`bg-${['info', 'secondary', 'success', 'warning', 'success', 'dark', 'danger'][barIndex]}`);
                }
            });
            console.log('Tab clicked:', this.id);
        });
    });

    nextButtons.forEach(button => {
        button.addEventListener('click', function () {
            const nextTabId = this.getAttribute('data-nexttab');
            const nextTab = document.getElementById(nextTabId);
            if (nextTab) {
                nextTab.click();
            }
        });
    });

    prevButtons.forEach(button => {
        button.addEventListener('click', function () {
            const prevTabId = this.getAttribute('data-previous');
            const prevTab = document.getElementById(prevTabId);
            if (prevTab) {
                prevTab.click();
            }
       

 });
    });

    // Form Validation
    function checkTabErrors(tabId) {
        const tabPane = document.querySelector(`#${tabId.replace('-tab', '')}`);
        const requiredInputs = tabPane.querySelectorAll('input[required], select[required], textarea[required]');
        let errors = [];
        requiredInputs.forEach(input => {
            if (!input.value.trim()) {
                errors.push(input);
            }
        });
        console.log('Tab errors checked:', { tabId, errors });
        return errors;
    }

    function validateTab(tabId) {
        const errors = checkTabErrors(tabId);
        const isValid = errors.length === 0;
        console.log('Tab validation:', { tabId, isValid });
        return isValid;
    }

    function updateSaveButton() {
        const requiredInputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let valid = true;
        requiredInputs.forEach(input => {
            if (!input.value.trim()) {
                valid = false;
            }
        });
        saveButton.disabled = !valid;
        console.log('Save button state updated. Valid:', valid, 'Required inputs:', requiredInputs.length);
    }

    navLinks.forEach(link => {
        const tabId = link.id;
        if (!validateTab(tabId)) {
            link.classList.add('invalid');
            console.log('Applied invalid to tab:', tabId);
        }
    });

    form.addEventListener('input', updateSaveButton);
    updateSaveButton();

    // Função para atualizar campos de renda e número de integrantes
    function updateFamiliaMetrics() {
        fetch(`/entrevistas/calcular_renda/${pacienteId}/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const numeroIntegrantes = document.getElementById('id_numero_integrantes');
                const rendaTotal = document.getElementById('id_renda_familiar_total');
                const rendaPerCapita = document.getElementById('id_renda_familiar_per_capita');
                if (numeroIntegrantes) numeroIntegrantes.value = data.numero_integrantes || '';
                if (rendaTotal) rendaTotal.value = data.renda_familiar_total || '';
                if (rendaPerCapita) rendaPerCapita.value = data.renda_familiar_per_capita || '';
            }
        })
        .catch(error => {
            console.error('Erro ao atualizar métricas de renda:', error);
        });
    }

    // Modal Handling with Error Checking
    function initializeModal(buttonId, modalId, formId, addUrl, deleteUrl, tableBodyId, rowTemplate) {
        const button = document.getElementById(buttonId);
        const modalElement = document.getElementById(modalId);
        const form = document.getElementById(formId);

        if (!button || !modalElement || !form) {
            console.error(`Modal initialization failed: ${buttonId}, ${modalId}, ${formId}`);
            return;
        }

        const modal = new bootstrap.Modal(modalElement, {});

        button.addEventListener('click', function () {
            form.reset();
            modal.show();
        });

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(form);
            formData.append('paciente_id', pacienteId);

            fetch(addUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const tbody = document.getElementById(tableBodyId);
                    const row = document.createElement('tr');
                    row.innerHTML = rowTemplate(data);
                    tbody.appendChild(row);
                    modal.hide();
                    showToast('successToast', `${buttonId.replace('inserir', '').replace('Btn', '')} adicionado com sucesso!`);
                    if (buttonId === 'inserirFamiliaBtn') updateFamiliaMetrics();
                } else {
                    showToast('errorToast', data.error || `Erro ao adicionar ${buttonId.replace('inserir', '').replace('Btn', '').toLowerCase()}.`);
                }
            })
            .catch(error => {
                showToast('errorToast', `Erro ao adicionar ${buttonId.replace('inserir', '').replace('Btn', '').toLowerCase()}.`);
                console.error('Error:', error);
            });
        });

        document.addEventListener('click', function (e) {
            if (e.target.classList.contains(`delete-${buttonId.replace('inserir', '').replace('Btn', '').toLowerCase()}`)) {
                const id = e.target.getAttribute('data-id');
                if (confirm(`Tem certeza que deseja excluir este ${buttonId.replace('inserir', '').replace('Btn', '').toLowerCase()}?`)) {
                    fetch(`${deleteUrl}${id}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            e.target.closest('tr').remove();
                            showToast('successToast', `${buttonId.replace('inserir', '').replace('Btn', '')} removido com sucesso!`);
                            if (buttonId === 'inserirFamiliaBtn') updateFamiliaMetrics();
                        } else {
                            showToast('errorToast', data.error || `Erro ao remover ${buttonId.replace('inserir', '').replace('Btn', '').toLowerCase()}.`);
                        }
                    })
                    .catch(error => {
                        showToast('errorToast', `Erro ao remover ${buttonId.replace('inserir', '').replace('Btn', '').toLowerCase()}.`);
                        console.error('Error:', error);
                    });
                }
            }
        });
    }

    // Initialize Modals
    initializeModal(
        'inserirDoadorBtn',
        'doadorModal',
        'doadorForm',
        '/entrevistas/adicionar_doador/',
        '/entrevistas/remover_doador/',
        'doadorTableBody',
        data => `
            <td>${data.doador.nome}</td>
            <td>${data.doador.cpf}</td>
            <td>${data.doador.rg || ''}</td>
            <td>${data.doador.estado_civil}</td>
            <td>${data.doador.sexo}</td>
            <td>${data.doador.nome_pai || ''}</td>
            <td>${data.doador.nome_mae || ''}</td>
            <td>${data.doador.escolaridade || ''}</td>
            <td>${data.doador.profissao || ''}</td>
            <td>${data.doador.endereco || ''}</td>
            <td>${data.doador.telefone || ''}</td>
            <td>${data.doador.email || ''}</td>
            <td>${data.doador.data_nascimento}</td>
            <td><button type="button" class="btn btn-danger btn-sm delete-doador" data-id="${data.doador.id}">Excluir</button></td>
        `
    );

    initializeModal(
        'inserirCuidadorBtn',
        'cuidadorModal',
        'cuidadorForm',
        '/entrevistas/adicionar_cuidador/',
        '/entrevistas/remover_cuidador/',
        'cuidadorTableBody',
        data => `
            <td>${data.cuidador.nome}</td>
            <td>${data.cuidador.grau_parentesco}</td>
            <td>${data.cuidador.telefone || ''}</td>
            <td>${data.cuidador.is_cuidador ? 'Sim' : 'Não'}</td>
            <td>${data.cuidador.is_responsavel ? 'Sim' : 'Não'}</td>
            <td><button type="button" class="btn btn-danger btn-sm delete-cuidador" data-id="${data.cuidador.id}">Excluir</button></td>
        `
    );

    initializeModal(
        'inserirFamiliaBtn',
        'familiaModal',
        'familiaForm',
        '/entrevistas/adicionar_composicao_familiar/',
        '/entrevistas/remover_composicao_familiar/',
        'familiaTableBody',
        data => `
            <td>${data.familiar.nome}</td>
            <td>${data.familiar.parentesco}</td>
            <td>${data.familiar.quantidade}</td>
            <td>${data.familiar.renda}</td>
            <td>${data.familiar.renda_sm || ''}</td>
            <td><button type="button" class="btn btn-danger btn-sm delete-familiar" data-id="${data.familiar.id}">Excluir</button></td>
        `
    );

    initializeModal(
        'inserirTransplanteBtn',
        'transplanteModal',
        'transplanteForm',
        '/entrevistas/adicionar_transplante/',
        '/entrevistas/remover_transplante/',
        'transplanteTableBody',
        data => `
            <td>${data.transplante.doenca_base}</td>
            <td>${data.transplante.tipo_sanguineo}</td>
            <td>${data.transplante.tipo_tratamento}</td>
            <td>${data.transplante.data_transplante || ''}</td>
            <td><button type="button" class="btn btn-danger btn-sm delete-transplante" data-id="${data.transplante.id}">Excluir</button></td>
        `
    );

    // Toast Function
    function showToast(toastId, message) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.querySelector('.toast-body').textContent = message;
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
        }
    }

    // Inicializar métricas de renda
    updateFamiliaMetrics();
});

    // Modal Handling for Composicao Familiar
    const inserirFamiliaBtn = document.getElementById('inserirFamiliaBtn');
    const familiaModal = new bootstrap.Modal(document.getElementById('familiaModal'), {});
    const familiaForm = document.getElementById('familiaForm');

    inserirFamiliaBtn.addEventListener('click', function () {
        familiaForm.reset();
        familiaModal.show();
    });

    familiaForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(familiaForm);
        formData.append('paciente_id', pacienteId);

        fetch('/entrevistas/adicionar_composicao_familiar/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tbody = document.getElementById('familiaTableBody');
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${data.familiar.nome}</td>
                    <td>${data.familiar.parentesco}</td>
                    <td>${data.familiar.quantidade}</td>
                    <td>${data.familiar.renda}</td>
                    <td>${data.familiar.renda_sm}</td>
                    <td><button type="button" class="btn btn-danger btn-sm delete-familiar" data-id="${data.familiar.id}">Excluir</button></td>
                `;
                tbody.appendChild(row);
                familiaModal.hide();
                showToast('successToast', 'Integrante familiar adicionado com sucesso!');
            } else {
                showToast('errorToast', data.error || 'Erro ao adicionar integrante familiar.');
            }
        })
        .catch(error => {
            showToast('errorToast', 'Erro ao adicionar integrante familiar.');
            console.error('Error:', error);
        });
    });

    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('delete-familiar')) {
            const familiarId = e.target.getAttribute('data-id');
            if (confirm('Tem certeza que deseja excluir este integrante familiar?')) {
                fetch(`/entrevistas/remover_composicao_familiar/${familiarId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        e.target.closest('tr').remove();
                        showToast('successToast', 'Integrante familiar removido com sucesso!');
                    } else {
                        showToast('errorToast', data.error || 'Erro ao remover integrante familiar.');
                    }
                })
                .catch(error => {
                    showToast('errorToast', 'Erro ao remover integrante familiar.');
                    console.error('Error:', error);
                });
            }
        }
    });

    // Toast Function
    function showToast(toastId, message) {
        const toast = document.getElementById(toastId);
        toast.querySelector('.toast-body').textContent = message;
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
});
