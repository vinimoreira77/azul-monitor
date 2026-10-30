document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('flights-grid');
    const sortSelect = document.getElementById('sort-select');
    const refreshBtn = document.getElementById('refresh-btn');
    const runBtn = document.getElementById('run-scraper-btn');
    const abortBtn = document.getElementById('abort-btn');
    const clearDataBtn = document.getElementById('clear-data-btn');
    const clearLogBtn = document.getElementById('clear-log-btn');
    const rawBox = document.getElementById('raw-json-box');
    const logBox = document.getElementById('log-box');
    const statusBadge = document.getElementById('status-badge');
    const routeTitle = document.getElementById('route-title');
    
    // Inputs
    const inputOrigin = document.getElementById('input-origin');
    const inputDest = document.getElementById('input-dest');
    const inputStart = document.getElementById('input-start');
    const inputEnd = document.getElementById('input-end');
    
    let flightsData = [];

    // Initialize dates defaults
    inputStart.value = '2027-04-01';
    inputEnd.value = '2027-05-30';

    // Helper: format number
    const formatNumber = (num) => new Intl.NumberFormat('pt-BR').format(num);

    const loadLogs = async () => {
        try {
            const res = await fetch('/api/logs');
            const data = await res.json();
            if (data.logs) {
                const isScrolledToBottom = logBox.scrollHeight - logBox.clientHeight <= logBox.scrollTop + 20;
                logBox.textContent = data.logs;
                if (isScrolledToBottom) {
                    logBox.scrollTop = logBox.scrollHeight;
                }
            } else {
                logBox.textContent = "Nenhum log disponível.";
            }
        } catch (e) {
            console.error("Erro ao carregar logs:", e);
        }
    };

    const checkStatus = async () => {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            
            if (data.status === 'running') {
                statusBadge.className = 'badge running';
                statusBadge.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Status: Rodando...';
                runBtn.style.display = 'none';
                abortBtn.style.display = 'flex';
                
                loadFlights(false);
                loadLogs();
            } else {
                statusBadge.className = 'badge idle';
                statusBadge.innerHTML = '<i class="fa-solid fa-power-off"></i> Status: Inativo';
                runBtn.style.display = 'flex';
                runBtn.disabled = false;
                abortBtn.style.display = 'none';
                runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Iniciar Varredura';
            }
        } catch (e) {
            console.error("Erro ao checar status", e);
        }
    };

    setInterval(checkStatus, 3000);

    const loadFlights = async (showSpinner = true) => {
        try {
            if (showSpinner) {
                grid.innerHTML = '<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Carregando voos...</div>';
            }
            const response = await fetch('/api/flights');
            const data = await response.json();
            
            flightsData = data.list;
            rawBox.textContent = JSON.stringify(data.raw, null, 2);
            
            renderDashboard();
        } catch (error) {
            console.error("Erro ao carregar voos:", error);
            if (showSpinner) {
                grid.innerHTML = '<div class="loading-state">Erro ao carregar os dados.</div>';
            }
        }
    };

    const renderDashboard = () => {
        if (flightsData.length === 0) {
            grid.innerHTML = '<div class="loading-state">Nenhum voo encontrado no histórico. Rode a varredura primeiro.</div>';
            
            document.getElementById('stat-days').innerText = '0';
            document.getElementById('stat-lowest').innerText = '0 pts';
            document.getElementById('stat-best-date').innerText = '-';
            return;
        }

        document.getElementById('stat-days').innerText = flightsData.length;
        
        const lowestPoints = Math.min(...flightsData.map(f => f.points));
        document.getElementById('stat-lowest').innerText = `${formatNumber(lowestPoints)} pts`;
        
        const bestFlight = flightsData.find(f => f.points === lowestPoints);
        const dateObj = new Date(bestFlight.date + "T00:00:00");
        document.getElementById('stat-best-date').innerText = dateObj.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
        
        // Update route title if we know it (assume origin and destination remain consistent for now, we could pull from inputs but inputs might change before run)
        routeTitle.innerText = `(${inputOrigin.value.toUpperCase()} ➔ ${inputDest.value.toUpperCase()})`;

        renderGrid();
    };

    const renderGrid = () => {
        grid.innerHTML = '';
        
        const sortBy = sortSelect.value;
        const sorted = [...flightsData].sort((a, b) => {
            if (sortBy === 'price') return a.points - b.points;
            return new Date(a.date) - new Date(b.date);
        });

        const DEAL_THRESHOLD = 35000;

        sorted.forEach(flight => {
            const isDeal = flight.points <= DEAL_THRESHOLD;
            const dateObj = new Date(flight.date + "T00:00:00");
            const formattedDate = dateObj.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
            const airline = flight.airline || "Azul";
            
            const card = document.createElement('div');
            card.className = `flight-card ${isDeal ? 'deal' : ''}`;
            card.title = `Partida: ${flight.departure} | Chegada: ${flight.arrival} | ${flight.points} pts`;
            
            card.innerHTML = `
                <div class="flight-date">${formattedDate}</div>
                <div class="flight-points">${(flight.points / 1000).toFixed(1)}k</div>
                <div class="flight-airline">${airline}</div>
            `;
            grid.appendChild(card);
        });
    };

    const showToast = (message) => {
        const toast = document.getElementById('toast');
        toast.innerText = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    };

    sortSelect.addEventListener('change', renderGrid);
    refreshBtn.addEventListener('click', () => {
        loadFlights();
        loadLogs();
        showToast("Dados atualizados!");
    });
    
    runBtn.addEventListener('click', async () => {
        const origin = inputOrigin.value.toUpperCase();
        const dest = inputDest.value.toUpperCase();
        const startDate = inputStart.value;
        const endDate = inputEnd.value;
        
        if(!origin || !dest || !startDate || !endDate) {
            showToast("Preencha todos os campos da configuração!");
            return;
        }

        try {
            await fetch('/api/run', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ origin, destination: dest, start_date: startDate, end_date: endDate })
            });
            showToast("Varredura iniciada!");
            routeTitle.innerText = `(${origin} ➔ ${dest})`;
            checkStatus();
        } catch(e) {
            showToast("Erro ao iniciar varredura.");
        }
    });

    abortBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/abort', { method: 'POST' });
            showToast("Aborto solicitado! O robô vai fechar no próximo dia.");
            setTimeout(checkStatus, 1500);
        } catch(e) {
            showToast("Erro ao abortar.");
        }
    });

    clearDataBtn.addEventListener('click', async () => {
        if(confirm("Tem certeza que quer apagar todos os voos salvos?")) {
            await fetch('/api/clear-data', { method: 'POST' });
            loadFlights();
            showToast("Dados apagados!");
        }
    });

    clearLogBtn.addEventListener('click', async () => {
        await fetch('/api/clear-logs', { method: 'POST' });
        loadLogs();
        showToast("Logs apagados!");
    });

    // Initial load
    checkStatus();
    loadFlights();
    loadLogs();
});
