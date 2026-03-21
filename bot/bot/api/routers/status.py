from fastapi import APIRouter
import bot.state as state

router = APIRouter()


@router.get("/status")
async def get_status():
    await state.position_manager.refresh()
    return state.get_status()


@router.post("/status/pause")
async def pause():
    state.guard.halt("MANUAL_PAUSE")
    return {"status": "paused"}


@router.post("/status/resume")
async def resume():
    state.guard.resume()
    return {"status": "running"}
