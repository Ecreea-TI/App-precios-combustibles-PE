document.addEventListener('DOMContentLoaded', () => {
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay d-none';
    loadingOverlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Cargando...</span>
        </div>
    `;
    document.body.appendChild(loadingOverlay);

    let currentData = [];
    let currentPage = 1;
    const itemsPerPage = 10;
    let totalPages = 0;

    const showLoading = () => loadingOverlay.classList.remove('d-none');
    const hideLoading = () => loadingOverlay.classList.add('d-none');

    const updatePagination = () => {
        const paginationContainer = document.querySelector('.pagination');
        const paginationInfo = document.querySelector('.pagination-info');
        
        if (!paginationContainer || !currentData.length) return;

        totalPages = Math.ceil(currentData.length / itemsPerPage);
        const startItem = (currentPage - 1) * itemsPerPage + 1;
        const endItem = Math.min(currentPage * itemsPerPage, currentData.length);

        paginationInfo.textContent = `Mostrando ${startItem} a ${endItem} de ${currentData.length} registros`;

        let paginationHTML = '';
        paginationHTML += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage - 1}">Anterior</a></li>`;
        
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                paginationHTML += `<li class="page-item ${i === currentPage ? 'active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                paginationHTML += `<li class="page-item disabled"><a class="page-link">...</a></li>`;
            }
        }

        paginationHTML += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage + 1}">Siguiente</a></li>`;
        paginationContainer.innerHTML = paginationHTML;

        document.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const newPage = parseInt(e.target.dataset.page);
                if (!isNaN(newPage) && newPage > 0 && newPage <= totalPages) {
                    currentPage = newPage;
                    renderTable();
                    updatePagination();
                }
            });
        });
    };

    const renderTable = () => {
        const tableBody = document.querySelector('tbody');
        if (!tableBody) return;

        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const pageData = currentData.slice(start, end);

        tableBody.innerHTML = pageData.map(item => `
            <tr>
                <td>${item.FCHA_REGISTRO || ''}</td>
                <td>${item.DEPARTAMENTO || ''}</td>
                <td>${item.PROVINCIA || ''}</td>
                <td>${item.DISTRITO || ''}</td>
                <td>${item.DIRECCION || ''}</td>
                <td>${item.RAZON_SOCIAL || ''}</td>
                <td>${item.TIPO_ESTABLECIMIENTO || ''}</td>
                <td>${item.PRODUCTO || ''}</td>
                <td>${item.PRECIO_VENTA || ''}</td>
                <td>${item.UNIDAD_MEDIDA || ''}</td>
            </tr>
        `).join('');
    };

    const fetchData = async (filters = {}) => {
        showLoading();
        try {
            let url = '/.netlify/functions/api/api/precios';
            const params = new URLSearchParams();
            
            if (filters.departamento) params.append('departamento', filters.departamento);
            if (filters.provincia) params.append('provincia', filters.provincia);
            if (filters.distrito) params.append('distrito', filters.distrito);
            
            if (params.toString()) url += `?${params.toString()}`;

            const response = await fetch(url);
            if (!response.ok) throw new Error('Error al obtener los datos');
            
            currentData = await response.json();
            currentPage = 1;
            renderTable();
            updatePagination();

            // Actualizar los selectores de filtros
            updateFilterOptions();
        } catch (error) {
            console.error('Error:', error);
            alert('Error al cargar los datos. Por favor, intente nuevamente.');
        } finally {
            hideLoading();
        }
    };

    const updateFilterOptions = () => {
        const departamentos = [...new Set(currentData.map(item => item.DEPARTAMENTO).filter(Boolean))];
        const provincias = [...new Set(currentData.map(item => item.PROVINCIA).filter(Boolean))];
        const distritos = [...new Set(currentData.map(item => item.DISTRITO).filter(Boolean))];
        const tiposEstablecimiento = [...new Set(currentData.map(item => item.TIPO_ESTABLECIMIENTO).filter(Boolean))];

        const departamentoSelect = document.getElementById('departamento');
        const provinciaSelect = document.getElementById('provincia');
        const distritoSelect = document.getElementById('distrito');
        const tipoEstablecimientoSelect = document.getElementById('tipoEstablecimiento');

        updateSelect(departamentoSelect, departamentos);
        updateSelect(provinciaSelect, provincias);
        updateSelect(distritoSelect, distritos);
        updateSelect(tipoEstablecimientoSelect, tiposEstablecimiento);
    };

    const updateSelect = (select, options) => {
        if (!select) return;
        const currentValue = select.value;
        select.innerHTML = '<option value="">Todos</option>';
        options.sort().forEach(option => {
            select.add(new Option(option, option));
        });
        select.value = currentValue;
    };

    // Event Listeners
    document.getElementById('departamento')?.addEventListener('change', () => {
        fetchData({
            departamento: document.getElementById('departamento').value,
            provincia: document.getElementById('provincia').value,
            distrito: document.getElementById('distrito').value
        });
    });

    document.getElementById('provincia')?.addEventListener('change', () => {
        fetchData({
            departamento: document.getElementById('departamento').value,
            provincia: document.getElementById('provincia').value,
            distrito: document.getElementById('distrito').value
        });
    });

    document.getElementById('distrito')?.addEventListener('change', () => {
        fetchData({
            departamento: document.getElementById('departamento').value,
            provincia: document.getElementById('provincia').value,
            distrito: document.getElementById('distrito').value
        });
    });

    document.getElementById('tipoEstablecimiento')?.addEventListener('change', (e) => {
        const tipo = e.target.value;
        if (tipo) {
            currentData = currentData.filter(item => item.TIPO_ESTABLECIMIENTO === tipo);
        }
        currentPage = 1;
        renderTable();
        updatePagination();
    });

    // Inicializar la aplicación
    fetchData();
}));