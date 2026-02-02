import requests
import threading
import time
from time import perf_counter
from queue import Queue

# ===========================
# CONFIG
# ===========================
DURATION = 60  # total test duration in seconds (adjust as needed)
TIMEOUT = 30   # HTTP timeout for each call
STRESS_LEVELS = [0, 5, 50]  # number of concurrent threads per stress level

# ===========================
# SERVICE CALLS
# ===========================
def call_generate_name():
    return requests.post(
        "http://generate-name-knative.pipeline.svc.cluster.local/run",
        files={
            "n_rows": (None, "1000"),
            "mf_ratio": (None, "0.5"),
            "output_path": (None, "/mnt/data/argo-shard/test/names.csv"),
        },
        timeout=TIMEOUT,
    )

def call_generate_birthday():
    return requests.post(
        "http://generate-birthday-knative.pipeline.svc.cluster.local/run",
        files={
            "n_rows": (None, "1000"),
            "min_age": (None, "18"),
            "max_age": (None, "80"),
            "output_file": (None, "/mnt/data/argo-shard/test/birthdays.csv"),
        },
        timeout=TIMEOUT,
    )

def call_generate_address():
    return requests.post(
        "http://generate-address-knative.pipeline.svc.cluster.local/run",
        files={
            "n_rows": (None, "1000"),
            "output_file": (None, "/mnt/data/argo-shard/test/addresses.csv"),
        },
        timeout=TIMEOUT,
    )

def call_generate_id():
    return requests.post(
        "http://generate-id-knative.pipeline.svc.cluster.local/run",
        files={
            "name_csv": (None, "/mnt/data/argo-shard/test/names.csv"),
            "birthday_csv": (None, "/mnt/data/argo-shard/test/birthdays.csv"),
            "output_file": (None, "/mnt/data/argo-shard/test/id.csv"),
        },
        timeout=TIMEOUT,
    )

def call_preprocess():
    return requests.post(
        "http://data-preprocess-knative.pipeline.svc.cluster.local/run",
        files={
            "metadata_file": (None, "/mnt/data/argo-shard/test/meta.json"),
            "input_file": (None, "/mnt/data/argo-shard/test/id.csv"),
            "output_file": (None, "/mnt/data/argo-shard/test/clean.csv"),
            "handle_missing": (None, "mean"),
        },
        timeout=TIMEOUT,
    )

def call_synth():
    return requests.post(
        "http://synthetic-generator-knative.pipeline.svc.cluster.local/run",
        files={
            "metadata_json": (None, "/mnt/data/argo-shard/test/meta.json"),
            "input_csv": (None, "clean.csv"),
            "input_dir": (None, "/mnt/data/argo-shard/test"),
            "output_file": (None, "/mnt/data/argo-shard/test/synth.csv"),
            "n_rows": (None, "1000"),
            "method": (None, "realistic"),
        },
        timeout=TIMEOUT,
    )

def call_quality():
    return requests.post(
        "http://data-quality-knative.pipeline.svc.cluster.local/run",
        files={
            "input_metadata_file": (None, "/mnt/data/argo-shard/test/meta.json"),
            "input_file_real": (None, "/mnt/data/argo-shard/test/clean.csv"),
            "input_file_synth": (None, "/mnt/data/argo-shard/test/synth.csv"),
            "output_dir": (None, "/mnt/data/argo-shard/test/quality"),
            "metrics": (None, "realistic"),
        },
        timeout=TIMEOUT,
    )

def call_privacy():
    return requests.post(
        "http://privacy-tracking-knative.pipeline.svc.cluster.local/run",
        files={
            "input_dir": (None, "/mnt/data/argo-shard/test"),
            "real_csv": (None, "clean.csv"),
            "synth_csv": (None, "synth.csv"),
            "output_file": (None, "/mnt/data/argo-shard/test/privacy.json"),
        },
        timeout=TIMEOUT,
    )

PIPELINE_CALLS = [
    call_generate_name,
    call_generate_birthday,
    call_generate_address,
    call_generate_id,
    call_preprocess,
    call_synth,
    call_quality,
    call_privacy,
]

# ===========================
# WORKER FUNCTION
# ===========================
def run_pipeline(stats_queue, thread_id):
    """Run the full pipeline repeatedly for DURATION seconds."""
    end_time = time.time() + DURATION
    while time.time() < end_time:
        for fn in PIPELINE_CALLS:
            start = perf_counter()
            try:
                r = fn()
                stats_queue.put((thread_id, r.status_code, perf_counter() - start))
            except Exception:
                stats_queue.put((thread_id, "ERR", 0))

# ===========================
# RUN STRESS LEVEL
# ===========================
def run_stress_level(users):
    print(f"\n=== Stress Level: {users} concurrent threads ===")
    stats_queue = Queue()
    threads = []

    # Launch threads
    for i in range(users if users > 0 else 1):
        t = threading.Thread(target=run_pipeline, args=(stats_queue, i))
        t.start()
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()

    # Collect stats
    stats = []
    while not stats_queue.empty():
        stats.append(stats_queue.get())

    ok = [s for s in stats if s[1] == 200]
    print(f"Total calls: {len(stats)} | Success: {len(ok)} | Failures: {len(stats)-len(ok)}")
    return stats

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    all_stats = {}
    for level in STRESS_LEVELS:
        stats = run_stress_level(level)
        all_stats[level] = stats
