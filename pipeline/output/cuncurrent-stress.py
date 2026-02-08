import requests
import threading
import time
from time import perf_counter
from queue import Queue

# ===========================
# CONFIG
# ===========================
DURATION = 600  # 10 minutes
TIMEOUT = 30
STRESS_LEVELS = [0, 5, 50]

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

SERVICES = {
    "generate-name": call_generate_name,
    "generate-birthday": call_generate_birthday,
    "generate-address": call_generate_address,
    "generate-id": call_generate_id,
    "preprocess": call_preprocess,
    "synth": call_synth,
    "quality": call_quality,
    "privacy": call_privacy,
}

# ===========================
# STRESS LEVEL RUNNER
# ===========================
def run_stress_level_all_services(users):
    print(f"\n=== Stress Level {users}: all services concurrently ===")

    stats_queue = Queue()
    threads = []

    thread_count = users if users > 0 else 1
    end_time = time.time() + DURATION

    def worker(service_name, service_fn, thread_id):
        while time.time() < end_time:
            start = perf_counter()
            try:
                r = service_fn()
                stats_queue.put(
                    (service_name, thread_id, r.status_code, perf_counter() - start)
                )
            except Exception:
                stats_queue.put((service_name, thread_id, "ERR", 0))

    for service_name, service_fn in SERVICES.items():
        for i in range(thread_count):
            t = threading.Thread(
                target=worker,
                args=(service_name, service_fn, i),
            )
            t.start()
            threads.append(t)

    for t in threads:
        t.join()

    stats = []
    while not stats_queue.empty():
        stats.append(stats_queue.get())

    for service_name in SERVICES.keys():
        service_stats = [s for s in stats if s[0] == service_name]
        ok = [s for s in service_stats if s[2] == 200]
        print(
            f"{service_name:20s} | "
            f"calls: {len(service_stats):6d} | "
            f"ok: {len(ok):6d} | "
            f"fail: {len(service_stats) - len(ok):6d}"
        )

    return stats

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    all_stats = {}

    for level in STRESS_LEVELS:
        all_stats[level] = run_stress_level_all_services(level)