/* assets/js/cuidador.js */
// Módulo para gerenciar cuidadores
(function() {
    const tableBody = document.getElementById('cuidadorTableBody');
    const inserirBtn = document.getElementById('inserirCuidadorBtn');
    let editMode = false;
    let editRow = null;

    // Adicionar novo cuidador
    if (inserirBtn) {
        inserirBtn.addEventListener('click', function() {
            removeExistingInputRow('inputRowCuidador');
            editMode = false;
            const inputRow = createInputRow();
            tableBody.appendChild(inputRow);
            bindInputEvents();
        });
    }

    // Criar linha de entrada
    function createInputRow(data = {}) {
        const inputRow = document.createElement('tr');
        inputRow.setAttribute('id', 'inputRowCuidador');
        inputRow.innerHTML = `
            <td><input type="text" class="form-control" id="nomeCuidadorInput" placeholder="Nome" value="${data.nome || ''}"></td>
            <td>
                <select class="form-select" id="grauParentescoInput">
                    <option value="mae" ${data.grauParentesco === 'mae' ? 'selected' : ''}>Mãe</option>
                    <option value="pai" ${data.grauParentesco === 'pai' ? 'selected' : ''}>Pai</option>
                    <option value="outro" ${data.grauParentesco === 'outro' ? 'selected' : ''}>Outro</option>
                </select>
            </td>
            <td><input type="text" class="form-control" id="telefoneCuidadorInput" placeholder="Telefone" value="${data.telefone || ''}"></td>
            <td>
                <select class="form-select" id="isCuidadorInput">
                    <option value="nao" ${data.isCuidador === 'nao' ? 'selected' : ''}>Não</option>
                    <option value="sim" ${data.isCuidador === 'sim' ? 'selected' : ''}>Sim</option>
                </select>
            </td>
            <td>
                <select class="form-select" id="isResponsavelInput">
                    <option value="nao" ${data.isResponsavel === 'nao' ? 'selected' : ''}>Não</option>
                    <option value="sim" ${data.isResponsavel === 'sim' ? 'selected' : ''}>Sim</option>
                </select>
            </td>
            <td>
                <button class="btn btn-success" id="saveCuidadorBtn">Salvar</button>
                <button class="btn btn-danger" id="cancelCuidadorBtn">Cancelar</button>
            </td>
        `;
        return inputRow;
    }

    // Vincular eventos aos inputs
    function bindInputEvents() {
        const nomeInput = document.getElementById('nomeCuidadorInput');
        nomeInput.addEventListener('input', function() {
            if (this.value.length < 3) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid').addClass('is-valid');
            }
        });

        document.getElementById('saveCuidadorBtn').onclick = saveCuidador;
        document.getElementById('cancelCuidadorBtn').onclick = function() {
            tableBody.removeChild(document.getElementById('inputRowCuidador'));
        };
    }

    // Salvar cuidador
    function saveCuidador() {
        const nome = document.getElementById('nomeCuidadorInput').value;
        if (!nome) {
            alert('O nome do cuidador é obrigatório.');
            return;
        }

        const cuidadorData = {
            nome: nome,
            grauParentesco: document.getElementById('grauParentescoInput').value,
            telefone: document.getElementById('telefoneCuidadorInput').value,
            isCuidador: document.getElementById('isCuidadorInput').value,
            isResponsavel: document.getElementById('isResponsavelInput').value
        };

        fetch('{% url "entrevistas:salvar_cuidador" paciente.id %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(cuidadorData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const newRow = document.createElement('tr');
                newRow.innerHTML = `
                    <td>${cuidadorData.nome}</td>
                    <td>${cuidadorData.grauParentesco}</td>
                    <td>${cuidadorData.telefone || '-'}</td>
                    <td>${cuidadorData.isCuidador === 'sim' ? 'Sim' : 'Não'}</td>
                    <td>${cuidadorData.isResponsavel === 'sim' ? 'Sim' : 'Não'}</td>
                    <td>
                        <button class="btn btn-warning editCuidadorBtn">Editar</button>
                        <button class="btn btn-danger deleteCuidadorBtn">Excluir</button>
                    </td>
                `;
                if (editMode && editRow) {
                    tableBody.replaceChild(newRow, editRow);
                } else {
                    tableBody.appendChild(newRow);
                }
                removeExistingInputRow('inputRowCuidador');
                showAlert('success', 'Cuidador salvo com sucesso!');
            } else {
                showAlert('danger', 'Erro ao salvar cuidador.');
            }
        });
    }

    // Editar cuidador
    tableBody.addEventListener('click', function(e) {
        if (e.target.classList.contains('editCuidadorBtn')) {
            editMode = true;
            editRow = e.target.closest('tr');
            const data = {
                nome: editRow.cells[0].textContent,
                grauParentesco: editRow.cells[1].textContent.toLowerCase(),
                telefone: editRow.cells[2].textContent === '-' ? '' : editRow.cells[2].textContent,
                isCuidador: editRow.cells[3].textContent.toLowerCase(),
                isResponsavel: editRow.cells[4].textContent.toLowerCase()
            };
            removeExistingInputRow('inputRowCuidador');
            const inputRow = createInputRow(data);
            tableBody.insertBefore(inputRow, editRow);
            bindInputEvents();
        } else if (e.target.classList.contains('deleteCuidadorBtn')) {
            if (confirm('Deseja excluir este cuidador?')) {
                tableBody.removeChild(e.target.closest('tr'));
                showAlert('success', 'Cuidador excluído com sucesso!');
            }
        }
    });

    // Remover linha de entrada existente
    function removeExistingInputRow(rowId) {
        const existingRow = document.getElementById(rowId);
        if (existingRow) {
            tableBody.removeChild(existingRow);
        }
    }

    // Mostrar alertas
    function showAlert(type, message) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        tableBody.parentElement.insertBefore(alert, tableBody);
        setTimeout(() => alert.classList.add('fade'), 3000);
    }
})();