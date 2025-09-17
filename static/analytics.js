// Analytics JavaScript

class AnalyticsManager {
    constructor() {
        this.charts = {};
        this.dateRange = '30d';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadAnalyticsData();
        this.initializeCharts();
    }

    setupEventListeners() {
        // Date range selector
        document.getElementById('dateRange').addEventListener('change', (e) => {
            this.dateRange = e.target.value;
            this.updateDateRange();
        });

        // Chart type buttons
        document.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const container = e.target.closest('.chart-container');
                const chartType = e.target.dataset.type;
                this.updateChartType(container, chartType);
            });
        });

        // Table search and filter
        document.getElementById('tableSearch').addEventListener('input', () => {
            this.filterTable();
        });

        document.getElementById('tableFilter').addEventListener('change', () => {
            this.filterTable();
        });

        // Comparison type selector
        document.getElementById('comparisonType').addEventListener('change', () => {
            this.updateComparisonChart();
        });
    }

    async loadAnalyticsData() {
        try {
            this.showLoading();
            
            // Simulate API calls for analytics data
            const [overviewData, consumptionData, applianceData, costData] = await Promise.all([
                this.fetchOverviewData(),
                this.fetchConsumptionData(),
                this.fetchApplianceData(),
                this.fetchCostData()
            ]);

            this.updateOverviewCards(overviewData);
            this.updateConsumptionChart(consumptionData);
            this.updateApplianceChart(applianceData);
            this.updateCostChart(costData);
            this.updatePeakUsageChart();
            this.updateComparisonChart();
            this.updateAnalyticsTable();
            
        } catch (error) {
            console.error('Error loading analytics data:', error);
            this.showError('Failed to load analytics data');
        }
    }

    async fetchOverviewData() {
        // Simulate API call
        return new Promise(resolve => {
            setTimeout(() => {
                resolve({
                    totalEnergy: 1247,
                    totalCost: 187.50,
                    efficiencyScore: 85,
                    carbonFootprint: 542,
                    changes: {
                        energy: -12,
                        cost: -8,
                        efficiency: 5,
                        carbon: -15
                    }
                });
            }, 500);
        });
    }

    async fetchConsumptionData() {
        // Generate sample consumption data
        const days = this.getDaysInRange();
        const data = [];
        
        for (let i = 0; i < days; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - 1 - i));
            data.push({
                date: date.toISOString().split('T')[0],
                consumption: Math.random() * 50 + 20 // 20-70 kWh
            });
        }
        
        return data;
    }

    async fetchApplianceData() {
        return [
            { name: 'Air Conditioner', consumption: 35.2, color: '#3b82f6' },
            { name: 'Refrigerator', consumption: 28.7, color: '#10b981' },
            { name: 'Water Heater', consumption: 18.3, color: '#f59e0b' },
            { name: 'Washing Machine', consumption: 12.1, color: '#8b5cf6' },
            { name: 'Television', consumption: 8.4, color: '#ef4444' },
            { name: 'Microwave', consumption: 4.8, color: '#06b6d4' }
        ];
    }

    async fetchCostData() {
        const days = Math.min(this.getDaysInRange(), 30);
        const data = [];
        
        for (let i = 0; i < days; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - 1 - i));
            data.push({
                date: date.toISOString().split('T')[0],
                cost: Math.random() * 15 + 5 // $5-20 per day
            });
        }
        
        return data;
    }

    getDaysInRange() {
        switch (this.dateRange) {
            case '24h': return 1;
            case '7d': return 7;
            case '30d': return 30;
            case '90d': return 90;
            case '1y': return 365;
            default: return 30;
        }
    }

    updateOverviewCards(data) {
        document.getElementById('totalEnergy').textContent = `${data.totalEnergy.toLocaleString()} kWh`;
        document.getElementById('totalCost').textContent = `$${data.totalCost.toFixed(2)}`;
        document.getElementById('efficiencyScore').textContent = `${data.efficiencyScore}%`;
        document.getElementById('carbonFootprint').textContent = `${data.carbonFootprint} kg CO₂`;

        // Update change indicators
        this.updateChangeIndicator('energy', data.changes.energy);
        this.updateChangeIndicator('cost', data.changes.cost);
        this.updateChangeIndicator('efficiency', data.changes.efficiency);
        this.updateChangeIndicator('carbon', data.changes.carbon);
    }

    updateChangeIndicator(type, change) {
        const cards = document.querySelectorAll('.overview-card');
        cards.forEach(card => {
            if (card.classList.contains(type)) {
                const indicator = card.querySelector('.metric-change');
                const isPositive = (type === 'efficiency' && change > 0) || 
                                 (type !== 'efficiency' && change < 0);
                
                indicator.className = `metric-change ${isPositive ? 'positive' : 'negative'}`;
                indicator.innerHTML = `
                    <i class="fas fa-arrow-${change > 0 ? 'up' : 'down'}"></i> 
                    ${Math.abs(change)}% vs last period
                `;
            }
        });
    }

    initializeCharts() {
        // Initialize empty charts
        this.charts.consumption = this.createConsumptionChart();
        this.charts.appliance = this.createApplianceChart();
        this.charts.cost = this.createCostChart();
        this.charts.peakUsage = this.createPeakUsageChart();
        this.charts.comparison = this.createComparisonChart();
    }

    createConsumptionChart() {
        const ctx = document.getElementById('consumptionChart').getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Energy Consumption (kWh)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#1f2937',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#10b981',
                        borderWidth: 1,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9'
                        },
                        ticks: {
                            color: '#64748b'
                        }
                    },
                    x: {
                        grid: {
                            color: '#f1f5f9'
                        },
                        ticks: {
                            color: '#64748b'
                        }
                    }
                }
            }
        });
    }

    createApplianceChart() {
        const ctx = document.getElementById('applianceChart').getContext('2d');
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [],
                    borderWidth: 0,
                    hoverBorderWidth: 2,
                    hoverBorderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            color: '#64748b'
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1f2937',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#10b981',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const percentage = ((context.parsed / context.dataset.data.reduce((a, b) => a + b)) * 100).toFixed(1);
                                return `${context.label}: ${context.parsed.toFixed(1)} kWh (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }

    createCostChart() {
        const ctx = document.getElementById('costChart').getContext('2d');
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Daily Cost ($)',
                    data: [],
                    backgroundColor: '#3b82f6',
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#1f2937',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9'
                        },
                        ticks: {
                            color: '#64748b',
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#64748b'
                        }
                    }
                }
            }
        });
    }

    createPeakUsageChart() {
        const ctx = document.getElementById('peakUsageChart').getContext('2d');
        return new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['12 AM', '3 AM', '6 AM', '9 AM', '12 PM', '3 PM', '6 PM', '9 PM'],
                datasets: [{
                    label: 'Energy Usage (kWh)',
                    data: [5, 3, 8, 15, 12, 18, 25, 20],
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 2,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9'
                        },
                        ticks: {
                            color: '#64748b'
                        },
                        pointLabels: {
                            color: '#64748b'
                        }
                    }
                }
            }
        });
    }

    createComparisonChart() {
        const ctx = document.getElementById('comparisonChart').getContext('2d');
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [
                    {
                        label: 'Current Period',
                        data: [85, 78, 92, 76],
                        backgroundColor: '#10b981',
                        borderRadius: 6
                    },
                    {
                        label: 'Previous Period',
                        data: [95, 88, 102, 86],
                        backgroundColor: '#e5e7eb',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#64748b',
                            usePointStyle: true
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9'
                        },
                        ticks: {
                            color: '#64748b'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#64748b'
                        }
                    }
                }
            }
        });
    }

    updateConsumptionChart(data) {
        this.charts.consumption.data.labels = data.map(d => this.formatDate(d.date));
        this.charts.consumption.data.datasets[0].data = data.map(d => d.consumption);
        this.charts.consumption.update();
    }

    updateApplianceChart(data) {
        this.charts.appliance.data.labels = data.map(d => d.name);
        this.charts.appliance.data.datasets[0].data = data.map(d => d.consumption);
        this.charts.appliance.data.datasets[0].backgroundColor = data.map(d => d.color);
        this.charts.appliance.update();
    }

    updateCostChart(data) {
        this.charts.cost.data.labels = data.map(d => this.formatDate(d.date));
        this.charts.cost.data.datasets[0].data = data.map(d => d.cost);
        this.charts.cost.update();
    }

    updatePeakUsageChart() {
        // Peak usage data is relatively static, just update if needed
        this.charts.peakUsage.update();
    }

    updateComparisonChart() {
        const comparisonType = document.getElementById('comparisonType').value;
        
        // Update chart based on comparison type
        let secondDataset;
        switch (comparisonType) {
            case 'previous':
                secondDataset = {
                    label: 'Previous Period',
                    data: [95, 88, 102, 86],
                    backgroundColor: '#e5e7eb'
                };
                break;
            case 'average':
                secondDataset = {
                    label: 'Average Household',
                    data: [110, 105, 115, 108],
                    backgroundColor: '#f59e0b'
                };
                break;
            case 'target':
                secondDataset = {
                    label: 'Target Goal',
                    data: [70, 68, 75, 72],
                    backgroundColor: '#ef4444'
                };
                break;
        }
        
        this.charts.comparison.data.datasets[1] = secondDataset;
        this.charts.comparison.update();
    }

    updateAnalyticsTable() {
        const tableBody = document.getElementById('analyticsTableBody');
        const appliances = [
            {
                name: 'Living Room AC',
                type: 'Air Conditioner',
                energy: 35.2,
                cost: 52.80,
                hours: 8.5,
                efficiency: 82,
                trend: 'up'
            },
            {
                name: 'Kitchen Fridge',
                type: 'Refrigerator',
                energy: 28.7,
                cost: 43.05,
                hours: 24,
                efficiency: 91,
                trend: 'down'
            },
            {
                name: 'Main Water Heater',
                type: 'Water Heater',
                energy: 18.3,
                cost: 27.45,
                hours: 4.2,
                efficiency: 75,
                trend: 'up'
            },
            {
                name: 'Laundry Washer',
                type: 'Washing Machine',
                energy: 12.1,
                cost: 18.15,
                hours: 2.1,
                efficiency: 88,
                trend: 'down'
            },
            {
                name: 'Master Bedroom TV',
                type: 'Television',
                energy: 8.4,
                cost: 12.60,
                hours: 6.3,
                efficiency: 93,
                trend: 'stable'
            },
            {
                name: 'Kitchen Microwave',
                type: 'Microwave',
                energy: 4.8,
                cost: 7.20,
                hours: 1.2,
                efficiency: 89,
                trend: 'down'
            }
        ];

        tableBody.innerHTML = appliances.map(appliance => `
            <tr>
                <td>${appliance.name}</td>
                <td>${appliance.type}</td>
                <td>${appliance.energy.toFixed(1)} kWh</td>
                <td>$${appliance.cost.toFixed(2)}</td>
                <td>${appliance.hours.toFixed(1)}h</td>
                <td>${appliance.efficiency}%</td>
                <td>
                    <span class="trend-indicator trend-${appliance.trend}">
                        <i class="fas fa-arrow-${appliance.trend === 'up' ? 'up' : appliance.trend === 'down' ? 'down' : 'right'}"></i>
                        ${appliance.trend === 'stable' ? 'Stable' : (appliance.trend === 'up' ? 'Increasing' : 'Decreasing')}
                    </span>
                </td>
                <td>
                    <button class="action-btn view-details-btn" onclick="viewApplianceDetails('${appliance.name}')">
                        View Details
                    </button>
                </td>
            </tr>
        `).join('');
    }

    updateChartType(container, chartType) {
        // Update active button
        container.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        container.querySelector(`[data-type="${chartType}"]`).classList.add('active');

        // Get chart canvas
        const canvas = container.querySelector('canvas');
        const chartId = canvas.id;

        // Destroy existing chart and create new one with different type
        if (this.charts[chartId.replace('Chart', '')]) {
            this.charts[chartId.replace('Chart', '')].destroy();
        }

        // Recreate chart with new type
        switch (chartId) {
            case 'consumptionChart':
                this.charts.consumption = this.createConsumptionChart();
                this.charts.consumption.config.type = chartType;
                break;
            case 'applianceChart':
                this.charts.appliance = this.createApplianceChart();
                this.charts.appliance.config.type = chartType;
                break;
            case 'costChart':
                this.charts.cost = this.createCostChart();
                this.charts.cost.config.type = chartType;
                break;
            case 'peakUsageChart':
                this.charts.peakUsage = this.createPeakUsageChart();
                this.charts.peakUsage.config.type = chartType;
                break;
        }

        // Reload data for the updated chart
        this.loadAnalyticsData();
    }

    updateDateRange() {
        this.loadAnalyticsData();
    }

    filterTable() {
        const searchTerm = document.getElementById('tableSearch').value.toLowerCase();
        const typeFilter = document.getElementById('tableFilter').value;
        const rows = document.querySelectorAll('#analyticsTableBody tr');

        rows.forEach(row => {
            const name = row.cells[0].textContent.toLowerCase();
            const type = row.cells[1].textContent.toLowerCase();
            
            const matchesSearch = name.includes(searchTerm) || type.includes(searchTerm);
            const matchesType = !typeFilter || type.includes(typeFilter.replace('_', ' '));
            
            row.style.display = matchesSearch && matchesType ? '' : 'none';
        });
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        if (this.dateRange === '24h') {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    }

    showLoading() {
        // You can implement loading states for each chart
        console.log('Loading analytics data...');
    }

    showError(message) {
        console.error(message);
        // You can implement error state UI here
    }
}

// Global functions
function exportAnalytics() {
    // Implement analytics export functionality
    alert('Exporting analytics data...');
}

function viewApplianceDetails(applianceName) {
    // Navigate to appliance details or open modal
    alert(`Viewing details for ${applianceName}`);
}

function logout() {
    window.location.href = '/login';
}

// Initialize analytics when page loads
let analyticsManager;
document.addEventListener('DOMContentLoaded', function() {
    analyticsManager = new AnalyticsManager();
});
