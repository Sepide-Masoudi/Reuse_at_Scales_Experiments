import requests
import threading
import time
from time import perf_counter
from queue import Queue
import argparse

# ===========================
# CONFIG
# ===========================
DURATION = 960  # 10 minutes per stress run
TIMEOUT = 300   # max wait for prime computation (seconds)

# ===========================
# PRIME SERVICE CALL
# ===========================
def call_prime_service(duration=240):
    """Call the prime service GET endpoint with a given duration in seconds."""
    url = f"http://130.149.158.132:31782/run?duration={duration}"
    return requests.get(url, timeout=TIMEOUT)

# ===========================
# STRESS LEVEL RUNNER
# ===========================
def run_stress_level_prime(users, duration=240):
    print(f"\n=== Stress Level {users}: prime service with duration={duration}s ===")

    stats_queue = Queue()
    threads = []

    thread_count = users if users > 0 else 1
    end_time = time.time() + DURATION

    def worker(thread_id):
        while time.time() < end_time:
            start = perf_counter()
            try:
                r = call_prime_service(duration)
                stats_queue.put(
                    ("prime-service", thread_id, r.status_code, perf_counter() - start)
                )
            except Exception:
                stats_queue.put(("prime-service", thread_id, "ERR", 0))

    for i in range(thread_count):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Collect stats
    stats = []
    while not stats_queue.empty():
        stats.append(stats_queue.get())

    ok = [s for s in stats if s[2] == 200]
    print(
        f"{'prime-service':20s} | "
        f"calls: {len(stats):6d} | "
        f"ok: {len(ok):6d} | "
        f"fail: {len(stats) - len(ok):6d}"
    )
    return stats

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run stress tests on the prime service")
    parser.add_argument(
        "stress", type=int, choices=[1, 5, 50],
        help="Stress factor (number of concurrent users: 1, 5, or 50)"
    )
    parser.add_argument(
        "--duration", type=int, default=240,
        help="Prime computation duration in seconds per request"
    )
    args = parser.parse_args()

    stress_factor = args.stress
    prime_duration = args.duration

    run_stress_level_prime(stress_factor, duration=prime_duration)