"""Visible terminal heartbeat while the actual headless pipeline runs.

Textual has closed before this context manager starts, so periodic output
confirms the process is alive without injecting progress widgets into the
experiment's acquisition loop or changing the random observer.
"""
from contextlib import contextmanager
import sys
from threading import Event, Thread


@contextmanager
def simulation_heartbeat(label: str = "Running virtual experiment", interval: float = 0.6):
    stop = Event()

    def show_progress():
        while not stop.wait(interval):
            sys.stdout.write(".")
            sys.stdout.flush()

    print(f"{label} ", end="", flush=True)
    thread = Thread(target=show_progress, daemon=True, name="psycolab-synthetic-progress")
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2)
        print(" finished", flush=True)
