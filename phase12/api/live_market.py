"""Live market dashboard and WebSocket endpoints.

This router exposes two endpoints:

* ``GET /live`` — returns a minimal HTML page that renders a real‑time
  chart of trade activity.  The page uses Chart.js for visualisation
  and connects to the ``/ws/trades`` WebSocket to receive trade
  updates.  When new trade events are broadcast they are appended to
  the chart and displayed with colour‑coded markers.

* ``/ws/trades`` — a WebSocket endpoint for streaming trade events.
  Clients connecting to this path will receive JSON messages when
  trades are executed via the REST API.  The payload contains the
  symbol, notional amount and timestamp.  The WebSocket listener is
  read–only; any received messages are ignored.

If you wish to customise the chart or send additional data, extend
the JavaScript embedded in the HTML below.  For production use you
should serve static assets from a CDN or integrate a templating
engine like Jinja2 instead of embedding scripts directly in the
endpoint.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..live_market import trade_notifier


router = APIRouter()


@router.get("/live", response_class=HTMLResponse)
async def get_live_dashboard() -> HTMLResponse:
    """Serve the live market dashboard page.

    The returned HTML includes a canvas element for Chart.js and a
    script that establishes a WebSocket connection to the server.  As
    trade events arrive, the chart updates in real time.  Colours are
    assigned based on whether the trade is a buy (green) or sell (red).
    """
    html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>Live Market Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1 { margin-bottom: 10px; }
    #chart-container { width: 100%; max-width: 800px; margin: auto; }
  </style>
  <!-- Load Chart.js from a CDN.  Replace with a local copy if required. -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>Live Market Trades</h1>
  <div id="chart-container">
    <canvas id="tradeChart"></canvas>
  </div>
  <script>
    // Initialise the chart with empty datasets
    const ctx = document.getElementById('tradeChart').getContext('2d');
    const data = {
      labels: [],
      datasets: [
        {
          label: 'Buy Notional',
          data: [],
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          tension: 0.1
        },
        {
          label: 'Sell Notional',
          data: [],
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.2)',
          tension: 0.1
        }
      ]
    };
    const config = {
      type: 'line',
      data: data,
      options: {
        responsive: true,
        scales: {
          x: {
            type: 'time',
            time: {
              parser: 'YYYY-MM-DDTHH:mm:ss.SSSZ',
              tooltipFormat: 'HH:mm:ss',
              unit: 'minute'
            },
            title: {
              display: true,
              text: 'Time'
            }
          },
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Notional (USD)'
            }
          }
        }
      }
    };
    const tradeChart = new Chart(ctx, config);

    // Open WebSocket connection
    const ws = new WebSocket(`ws://${location.host}/ws/trades`);
    ws.onmessage = function(event) {
      const msg = JSON.parse(event.data);
      const now = new Date();
      // Append data to appropriate dataset
      tradeChart.data.labels.push(now);
      if (msg.action === 'BUY') {
        tradeChart.data.datasets[0].data.push(msg.notional);
        tradeChart.data.datasets[1].data.push(null);
      } else {
        tradeChart.data.datasets[0].data.push(null);
        tradeChart.data.datasets[1].data.push(msg.notional);
      }
      tradeChart.update();
    };
    ws.onclose = function() {
      console.log('WebSocket connection closed');
    };
  </script>
</body>
</html>
    """
    return HTMLResponse(content=html, status_code=200)


@router.websocket("/ws/trades")
async def trade_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint that streams trade events to clients.

    This handler registers the client with the global ``trade_notifier``
    and keeps the connection open until the client disconnects.  Any
    data sent from the client is read and ignored; this endpoint is
    publish‑only from the server.
    """
    await trade_notifier.connect(websocket)
    try:
        while True:
            # Block until the client sends a message or disconnects.
            # We ignore incoming messages, but ``receive_text`` is used
            # instead of ``receive_json`` to avoid parsing overhead.
            await websocket.receive_text()
    except WebSocketDisconnect:
        trade_notifier.disconnect(websocket)
