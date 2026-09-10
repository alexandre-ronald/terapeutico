/* assets/js/doador.js */
// Módulo para gerenciar doadores
(function() {
    const tableBody = document.getElementById('doadorTableBody');
    const inserirBtn = document.getElementById('inserirDoadorBtn');
    let editMode = false;
    let editRow = null;

    // Adicionar novo doador
    if (inserirBtn) {
        inserirBtn.addEventListener('click', function() {
            removeExistingInputRow('inputRowDoador');
            editMode = false;
            const inputRow = createInputRow();
            tableBody.appendChild(inputRow);
            bindInputEvents();
        });
    }

    // Criar linha de entrada
    function createInputRow(data = {}) {
        const inputRow = document.createElement('tr');
        inputRow.setAttribute('id', 'inputRowDoador');
        inputRow.innerHTML = `
            <td><input type="text" class="form-control" id="nomeDoadorInput" placeholder="Nome" value="${data.nome || ''}"></td>
            <td><input type="text" class="form-control" id="cpfInput" placeholder="CPF" value="${data.cpf || ''}"></td>
            <td><input type="text" class="form-control" id="rgInput" placeholder="RG" value="${data.rg || ''}"></td>
            <td>
                <select class="form-select" id="estadoCivilInput">
                    <option value="solteiro" ${data.estadoCivil === 'solteiro' ? 'selected' : ''}>Solteiro</option>
                    <option value="casado" ${data.estadoCivil === 'casado' ? 'selected' : ''}>Casado</option>
                    <option value="divorciado" ${data.estadoCivil === 'divorciado' ? 'selected' : ''}>Divorciado</option>
                    <option value="viuvo" ${data.estadoCivil === 'viuvo' ? 'selected' : ''}>Viúvo</option>
                </select>
            </td>
            <td><input type="text" class="form-control" id="telefoneDoadorInput" placeholder="Telefone" value="${data.telefone || ''}"></td>
            <td><input type="date" class="form-control" id="dataNascimentoInput" value="${data.dataNascimento || ''}"></td>
            <td>
                <button class="btn btn-success" id="saveDoadorBtn">Salvar</button>
                <button class="btn btn-danger" id="cancelDoadorBtn">Cancelar</button>
            </td>
        `;
        return inputRow;
    }

    // Vincular eventos aos inputs
    function bindInputEvents() {
        const nomeInput = document.getElementById('nomeDoadorInput');
        const cpfInput = document.getElementById('cpfInput');
        nomeInput.addEventListener('input', function() {
            if (this.value.length < 3) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid').addClass('is-valid');
            }
        });
        cpfInput.addEventListener('input', function() {
            if (!/^\d{11}$/.test(this.value)) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid').addClass('is-valid');
            }
        });

        document.getElementById('saveDoadorBtn').onclick = saveDoador;
        document.getElementById('cancelDoadorBtn').onclick = function() {
            tableBody.removeChild(document.getElementById('inputRowDoador'));
        };
    }

    // Salvar doador
    function saveDoador() {
        const nome = document.getElementById('nomeDoadorInput').value;
        const cpf = document.getElementById('cpfInput').value;
        if (!nome || !cpf) {
            alert('Nome e CPF do doador são obrigatórios.');
            return;
        }

        const doadorData = {
            nome: nome,
            cpf: cpf,
            rg: document.getElementById('rgInput').value,
            estadoCivil: document.getElementById('estadoCivilInput').value,
            telefone: document.getElementById('telefoneDoadorInput').value,
            dataNascimento: document.getElementById('dataNascimentoInput').value
        };

        fetch('{% url "entrevistas:salvar_doador" paciente.id %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(doadorData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const newRow = document.createElement('tr');
                newRow.innerHTML = `
                    <td>${doadorData.nome}</td>
                    <td>${doadorData.cpf}</td>
                    <td>${doadorData.rg || '-'}</td>
                    <td>${doadorData.estadoCivil.charAt(0).toUpperCase() + doadorData.estadoCivil.slice(1)}</td>
                    <td>${doadorData.telefone || '-'}</td>
                    <td>${doadorData.dataNascimento}</td>
                    <td>
                        <button class="btn btn-warning editDoadorBtn">Editar</button>
                        <button class="btn btn-danger deleteDoadorBtn">Excluir</button>
                    </td>
                `;
                if (editMode && editRow) {
                    tableBody.replaceChild(newRow, editRow);
                } else {
                    tableBody.appendChild(newRow);
                }
                removeExistingInputRow('inputRowDoador');
                showAlert('success', 'Doador salvo com sucesso!');
            } else {
                showAlert('danger', 'Erro ao salvar doador.');
            }
        });
    }

    // Editar doador
    tableBody.addEventListener('click', function(e) {
        if (e.target.classList.contains('editDoadorBtn')) {
            editMode = true;
            editRow = e.target.closest('tr');
            const data = {
                nome: editRow.cells[0].textContent,
                cpf: editRow.cells[1].textContent,
                rg: editRow.cells[2].textContent === '-' ? '' : editRow.cells[2].textContent,
                estadoCivil: editRow.cells[3].textContent.toLowerCase(),
                telefone: editRow.cells[4].textContent === '-' ? '' : editRow.cells[4].textContent,
                dataNascimento: editRow.cells[5].textContent
            };
            removeExistingInputRow('inputRowDoador');
            const inputRow = createInputRow(data);
            tableBody.insertBefore(inputRow, editRow);
            bindInputEvents();
        } else if (e.target.classList.contains('deleteDoadorBtn')) {
            if (confirm('Deseja excluir este doador?')) {
                tableBody.removeChild(e.target.closest('tr'));
                showAlert('success', 'Doador excluído com sucesso!');
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