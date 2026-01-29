/* =========================
   Retail Analytics Dashboard
   ========================= */

const API_BASE = "/api"; // backend base route

let hourlyChart = null;
let realtimeChart = null;
let realtimeData = [];
let realtimeLabels = [];

/* ---------- Connection Status ---------- */
function setConnectionStatus(online) {
    const dot = document.getElementById("connection-status");
    const text = document.getElementById("status-text");

    if (online) {
        dot.classList.remove("offline");
        dot.classList.add("online");
        text.textContent = "Connected";
    } else {
        dot.classList.remove("online");
        dot.classList.add("offline");
        text.textContent = "Disconnected";
    }
}

/* ---------- Stats ---------- */
function updateStats(data) {
    document.getElementById("current-count").textContent = data.current_occupancy;
    document.getElementById("total-footfall").textContent = data.today_footfall;
    document.getElementById("peak-count").textContent = data.peak.count;
    document.getElementById("peak-time").textContent = data.peak.time;
    document.getElementById("active-cameras").textContent = data.active_cameras;
}

/* ---------- Video Feeds ---------- */
function renderCameras(cameras) {
    const grid = document.getElementById("video-grid");
    grid.innerHTML = "";

    cameras.forEach(cam => {
        const div = document.createElement("div");
        div.className = "video-card";
        div.innerHTML = `
            <h4>${cam.name}</h4>
            <img src="${cam.stream_url}" alt="${cam.name}">
        `;
        grid.appendChild(div);
    });
}

/* ---------- Zone Analytics ---------- */
function renderZones(zones) {
    const grid = document.getElementById("zone-grid");
    grid.innerHTML = "";

    zones.forEach(zone => {
        const div = document.createElement("div");
        div.className = "zone-card";
        div.innerHTML = `
            <h4>${zone.name}</h4>
            <p>People: <strong>${zone.count}</strong></p>
            <p>Dwell Time: ${zone.dwell_time}s</p>
        `;
        grid.appendChild(div);
    });
}

/* ---------- Charts ---------- */
function initHourlyChart(labels, data) {
    const ctx = document.getElementById("hourly-chart").getContext("2d");

    if (hourlyChart) hourlyChart.destroy();

    hourlyChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Footfall",
                data,
                backgroundColor: "#4f46e5"
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function initRealtimeChart() {
    const ctx = document.getElementById("realtime-chart").getContext("2d");

    realtimeChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: realtimeLabels,
            datasets: [{
                label: "Occupancy",
                data: realtimeData,
                borderColor: "#16a34a",
                tension: 0.3
            }]
        },
        options: {
            animation: false,
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function updateRealtimeChart(value) {
    const time = new Date().toLocaleTimeString();

    realtimeLabels.push(time);
    realtimeData.push(value);

    if (realtimeLabels.length > 20) {
        realtimeLabels.shift();
        realtimeData.shift();
    }

    realtimeChart.update();
}

/* ---------- Heatmap ---------- */
function updateHeatmap(url) {
    document.getElementById("heatmap-image").src = url + "?t=" + Date.now();
}

/* ---------- Footer ---------- */
function updateLastUpdated() {
    document.getElementById("last-update").textContent =
        new Date().toLocaleString();
}

/* ---------- API Fetch ---------- */
async function fetchDashboardData() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`);
        if (!res.ok) throw new Error("API error");

        const data = await res.json();
        setConnectionStatus(true);

        updateStats(data.stats);
        renderCameras(data.cameras);
        renderZones(data.zones);
        initHourlyChart(data.hourly.labels, data.hourly.values);
        updateRealtimeChart(data.stats.current_occupancy);
        updateHeatmap(data.heatmap_url);
        updateLastUpdated();

    } catch (err) {
        console.error(err);
        setConnectionStatus(false);
    }
}

/* ---------- Init ---------- */
function init() {
    initRealtimeChart();
    fetchDashboardData();
    setInterval(fetchDashboardData, 5000); // refresh every 5s
}

document.addEventListener("DOMContentLoaded", init);
