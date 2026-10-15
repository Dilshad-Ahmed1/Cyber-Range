import asyncio

from server.live_server import LiveSession


def test_stopping_active_live_trial_cancels_task():
    async def exercise_stop():
        live_session = LiveSession()
        started = asyncio.Event()

        async def wait_for_stop():
            started.set()
            await asyncio.Event().wait()

        live_session.trial_id = "trial-test"
        live_session.task = asyncio.create_task(wait_for_stop())
        await started.wait()

        result = await live_session.stop()

        assert result["stopped"]
        assert not result["running"]
        assert result["trial_id"] == "trial-test"
        assert live_session.task is None

    asyncio.run(exercise_stop())


def test_stopping_when_idle_is_idempotent():
    async def exercise_stop():
        result = await LiveSession().stop()

        assert not result["stopped"]
        assert not result["running"]

    asyncio.run(exercise_stop())