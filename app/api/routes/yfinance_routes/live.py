import asyncio
from contextlib import suppress
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import yfinance as yf

router = APIRouter(prefix="/live", tags=["Live"])


@router.websocket("/quotes")
async def live_quotes(websocket: WebSocket):
    await websocket.accept()

    print("Connected to WebSocket for live quotes.")

    symbols_param = websocket.query_params.get("symbols", "")
    symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()]

    if not symbols:
        await websocket.send_json({"error": "No symbols provided"})
        await websocket.close()
        return

    queue: asyncio.Queue[dict] = asyncio.Queue()
    yf_ws: yf.AsyncWebSocket | None = None

    async def handle_message(message: dict):
        await queue.put(message)

    async def yfinance_stream():
        nonlocal yf_ws

        yf_ws = yf.AsyncWebSocket(verbose=False)

        try:
            await yf_ws.subscribe(symbols)
            print(f"Subscribed to symbols: {symbols}")

            await yf_ws.listen(handle_message)

        except asyncio.CancelledError:
            print("YFinance stream cancelled.")
            raise

        finally:
            print("Closing yfinance websocket...")
            with suppress(Exception):
                await yf_ws.close()

    async def client_disconnect_watcher():
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            print("Client disconnected.")
        except Exception as e:
            print(f"Client watcher stopped: {e}")

    stream_task = asyncio.create_task(yfinance_stream())
    disconnect_task = asyncio.create_task(client_disconnect_watcher())

    try:
        while True:
            done, pending = await asyncio.wait(
                {
                    asyncio.create_task(queue.get()),
                    disconnect_task,
                    stream_task,
                },
                return_when=asyncio.FIRST_COMPLETED,
            )

            if disconnect_task in done:
                print("Disconnect detected. Stopping stream.")
                break

            if stream_task in done:
                print("YFinance stream ended.")
                break

            for task in done:
                message = task.result()

                payload = {
                    "symbol": message.get("id") or message.get("symbol"),
                    "currency": message.get("currency"),
                    "price": message.get("price"),
                    "change": message.get("change"),
                    "change_percent": message.get("change_percent"),
                    "volume": message.get("day_volume") or message.get("volume"),
                    "market_state": message.get("market_hours"),
                    "timestamp": message.get("time"),
                    "raw": message,
                }

                await websocket.send_json(payload)

            for task in pending:
                if task is not disconnect_task and task is not stream_task:
                    task.cancel()

    finally:
        print("Cleaning up websocket tasks...")

        stream_task.cancel()
        disconnect_task.cancel()

        with suppress(Exception):
            await stream_task

        with suppress(Exception):
            await disconnect_task

        if yf_ws:
            with suppress(Exception):
                await yf_ws.close()

        print("Cleanup complete.")